from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List                          # Burada değişiklik var: artık API giriş tipi liste olacak
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# FastAPI uygulaması başlatılır
app = FastAPI(title="Toplu Satış Tahmini API", version="1.0")

# Eğitimli model yüklenir
try:
    model = joblib.load("rf_model.pkl")
except Exception as e:
    raise RuntimeError("Model yüklenemedi: " + str(e))

# Ortam değişkenleri yüklenir ve veritabanı bağlantısı kurulur
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Girdi yapısı tanımlanır
class PredictionInput(BaseModel):
    product_id: int = Field(..., description="Tahmin yapılacak ürün ID’si")
    unit_price: float = Field(..., description="Ürünün birim fiyatı")
    quantity: int = Field(..., description="Sipariş edilen miktar")
    order_date: str = Field(..., description="Sipariş tarihi (YYYY-MM-DD formatında)")

# Tahmin endpoint'i tanımlanır
# DEĞİŞEN YER: Artık tek bir input değil, bir liste alıyoruz → bu sayede çoklu tahmin yapılabiliyor
@app.post("/predict/batch", tags=["Toplu Tahmin"])
def predict_batch(inputs: List[PredictionInput]):
    feature_list = []   # Her siparişe ait model girdileri burada toplanacak
    results = []        # Her tahmine ait açıklayıcı veriler burada saklanacak

    # Tüm giriş verileri üzerinde döngü kurulur
    for input in inputs:
        # Sipariş tarihi string formatından datetime nesnesine çevrilir
        try:
            order_date = pd.to_datetime(input.order_date)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Tarih formatı hatalı: {input.order_date}")

        # Tarihten yıl, ay ve haftanın günü bilgileri çıkarılır (otomatik)
        month = order_date.month
        year = order_date.year
        day_of_week = order_date.dayofweek

        # Mevsim bilgisi ay üzerinden belirlenir
        def get_season(month):
            if month in [3, 4, 5]:
                return 1  # İlkbahar
            elif month in [6, 7, 8]:
                return 2  # Yaz
            elif month in [9, 10, 11]:
                return 3  # Sonbahar
            else:
                return 4  # Kış

        season = get_season(month)

        # Ürünün adı ve ülke bilgisi veritabanından çekilir
        try:
            query = f"""
                SELECT p.product_name, c.country
                FROM products p
                JOIN order_details od ON p.product_id = od.product_id
                JOIN orders o ON od.order_id = o.order_id
                JOIN customers c ON o.customer_id = c.customer_id
                WHERE p.product_id = {input.product_id}
                ORDER BY o.order_date DESC
                LIMIT 1
            """
            result = pd.read_sql(query, engine)

            if result.empty:
                raise HTTPException(status_code=404, detail=f"Ürün verisi bulunamadı: {input.product_id}")

            row = result.iloc[0]
            # Ürün adı ve ülke bilgisi kategorik sayıya çevrilir
            product_code = int(pd.Series(row['product_name']).astype("category").cat.codes[0])
            country_code = int(pd.Series(row['country']).astype("category").cat.codes[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Veri çekilirken hata: {str(e)}")

        # Ortalama fiyat input'tan alınır (istersen burada farklı stratejiler kullanabilirsin)
        avg_price = input.unit_price

        # Modelin beklediği sıraya göre özellik vektörü hazırlanır
        feature_vector = [
            month,
            year,
            day_of_week,
            season,
            country_code,
            product_code,
            input.quantity,
            input.unit_price,
            avg_price
        ]

        feature_list.append(feature_vector)  # Bu tahmin için satır eklendi

        # Girdiye dair açıklayıcı bilgiler sonuca eklenmek üzere kaydedilir
        results.append({
            "product_id": input.product_id,
            "unit_price": input.unit_price,
            "quantity": input.quantity,
            "order_date": input.order_date,
            "season": season,
            "country_code": country_code,
            "product_code": product_code
        })

    # DEĞİŞEN YER: Artık model.predict() çoklu veriyle çağrılır → tek tek değil topluca tahmin yapılır
    try:
        features = np.array(feature_list)
        predictions = model.predict(features)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tahmin hatası: {str(e)}")

    # Tüm tahmin sonuçları birleştirilerek kullanıcıya anlamlı şekilde döndürülür
    output = []
    for i, prediction in enumerate(predictions):
        output.append({
            "tahmin_edilen_satis_tutari": round(float(prediction), 2),
            "girdi_ozeti": results[i]
        })

    return output
