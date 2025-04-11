from fastapi import FastAPI, HTTPException           # FastAPI uygulaması ve hata yönetimi için
from pydantic import BaseModel, Field                # Veri doğrulama ve Swagger açıklamaları için
import joblib                                        # Eğitimli modeli .pkl dosyasından yüklemek için
import numpy as np                                   # Sayısal hesaplama işlemleri için
import pandas as pd                                  # Veri analizi ve veritabanı işlemleri için
from sqlalchemy import create_engine                 # SQL veritabanı bağlantısı kurmak için
from dotenv import load_dotenv                       # Ortam değişkenlerini .env dosyasından çekmek için
import os                                            # Ortam değişkenlerini okumak için kullanılır

# FastAPI uygulaması başlatılır
app = FastAPI(title="Satış Tahmini API", version="1.0")

# Eğitimli model dosyası yüklenir
try:
    model = joblib.load("rf_model.pkl")
except Exception as e:
    raise RuntimeError("Model yüklenemedi: " + str(e))

# Ortam değişkenleri yüklenir ve veritabanına bağlantı kurulur
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# API'den gelecek veri yapısı tanımlanır
class PredictionInput(BaseModel):
    product_id: int = Field(..., description="Tahmin yapılacak ürünün ID'si. Veritabanındaki product_id ile eşleşmelidir.")
    unit_price: float = Field(..., description="Ürünün satış birim fiyatı. Tahmin girişinde kullanılır.")
    quantity: int = Field(..., description="Sipariş edilen ürün miktarı.")
    order_date: str = Field(..., description="Sipariş tarihi. Format: YYYY-MM-DD (örnek: 2024-12-31)")

# Tahmin yapılacak endpoint
@app.post("/predict", tags=["Satış Tahmini"])
def predict(input: PredictionInput):
    # Tarih formatı kontrol edilir ve datetime formatına dönüştürülür
    try:
        order_date = pd.to_datetime(input.order_date)
    except Exception:
        raise HTTPException(status_code=400, detail="Tarih formatı hatalı. YYYY-MM-DD kullanın.")

    # order_date'ten otomatik olarak tarih bileşenleri çıkarılır (kullanıcıdan ayrı olarak gelir)
    month = order_date.month
    year = order_date.year
    day_of_week = order_date.dayofweek  # Pazartesi = 0, Pazar = 6

    # Mevsim bilgisi ay verisinden hesaplanır, kullanıcıdan gönderilmez
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

    # Ürün adı ve ülke bilgisi veritabanından çekilir, kullanıcı yalnızca product_id gönderir
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

        # Eğer ürün daha önce sipariş edilmemişse hata döndürülür
        if result.empty:
            raise HTTPException(status_code=404, detail="Ürün verisi bulunamadı.")

        row = result.iloc[0]

        # Aşağıdaki değişkenler veritabanından gelen değerlere göre otomatik oluşturulur
        product_code = int(pd.Series(row['product_name']).astype("category").cat.codes[0])  # Ürün adı kategorik koda çevrilir
        country_code = int(pd.Series(row['country']).astype("category").cat.codes[0])       # Ülke adı kategorik koda çevrilir
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veri çekilirken hata: {str(e)}")

    # Ortalama fiyat şimdilik input'tan alınır, ama ileride veritabanından da hesaplanabilir
    avg_price = input.unit_price

    # Özellik vektörü oluşturulur, sırayla modelle uyumlu olacak şekilde hazırlanır
    # scikit-learn modelleri girdi olarak 2 boyutlu array bekler
    # Burada sadece 1 örnek verdiğimiz için dıştaki [[...]] şeklinde tek bir satırlık matris oluşturuyoruz.
    features = np.array([[ 
        month,             # Siparişin verildiği ay (1-12) → Mevsimsel etkileri öğrenmek için
        year,              # Sipariş yılı (örneğin: 2025) → Zamanla artan veya azalan trendleri öğrenmek için
        day_of_week,       # Haftanın günü (0 = Pazartesi, 6 = Pazar) → Hangi gün daha çok satış yapılıyor?
        season,            # Ay bilgisine göre belirlenen mevsim (1 = İlkbahar, 2 = Yaz, 3 = Sonbahar, 4 = Kış)
        country_code,      # Siparişin gönderildiği ülkenin kategorik kodu (ülke ismi → sayısal koda çevrildi)
        product_code,      # Ürünün adı üzerinden oluşturulan kategorik kod (modelin metinle uğraşmasına gerek kalmaz)
        input.quantity,    # Sipariş edilen ürün miktarı (girdi olarak kullanıcıdan gelir)
        input.unit_price,  # Ürünün birim fiyatı (girdi olarak kullanıcıdan gelir)
        avg_price          # Ortalama fiyat (şu an sabit olarak input.unit_price, ileride ürünün genel ortalaması alınabilir)
    ]])

    # Model kullanılarak tahmin yapılır
    try:
        prediction = model.predict(features)[0]
        # Bu çıktı, her örnek için 1 tahmin değeri içerir.
        # Biz sadece 1 örnek gönderdiğimiz için sonuç: 1 elemanlı array
        # Bu, dönen array’den ilk ve tek tahmin değerini alır.       
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tahmin hatası: {str(e)}")

    # Tahmin ve özet bilgiler API yanıtı olarak döndürülür
    return {
        "tahmin_edilen_satis_tutari": round(float(prediction), 2),
        "girdi_ozeti": {
            "product_id": input.product_id,
            "unit_price": input.unit_price,
            "quantity": input.quantity,
            "order_date": input.order_date,
            "season": season,               # Koddan otomatik üretildi
            "country_code": country_code,   # Veritabanından geldi
            "product_code": product_code    # Veritabanından geldi
        }
    }
