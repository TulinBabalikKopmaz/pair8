from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

app = FastAPI(title="Satış Tahmini API", version="2.0")

# Model ve veri yükleme
try:
    model = joblib.load("sales_model.pkl")
    product_code_map = joblib.load("product_code_map.pkl")
except Exception as e:
    raise RuntimeError("Model veya eşleme dosyası yüklenemedi: " + str(e))

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

class PredictionInput(BaseModel):
    product_id: int
    unit_price: float
    order_date: str  # YYYY-MM-DD

@app.post("/predict", tags=["Tahmin"])
def predict(input: PredictionInput):
    try:
        order_date = pd.to_datetime(input.order_date)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz tarih formatı. YYYY-MM-DD kullanın.")

    prev_month = (order_date - pd.DateOffset(months=1)).strftime('%Y-%m')
    order_month_num = int(order_date.strftime('%Y%m'))
    month_only = order_date.month

    # Ürün adı bul
    try:
        product_query = f"SELECT product_name FROM products WHERE product_id = {input.product_id}"
        product_result = pd.read_sql(product_query, engine)
        if product_result.empty:
            raise HTTPException(status_code=404, detail="Ürün bulunamadı.")
        product_name = product_result['product_name'].iloc[0]
        if product_name not in product_code_map:
            raise HTTPException(status_code=400, detail="Ürün eğitim verisinde yok.")
        product_code = product_code_map[product_name]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ürün kodu belirlenirken hata: {str(e)}")

    # Önceki ay satış
    try:
        prev_q = f"""
            SELECT SUM(od.quantity) AS prev_month_sales
            FROM order_details od
            JOIN orders o ON od.order_id = o.order_id
            WHERE od.product_id = {input.product_id}
            AND TO_CHAR(o.order_date, 'YYYY-MM') = '{prev_month}'
        """
        prev_df = pd.read_sql(prev_q, engine)
        if prev_df.empty or prev_df['prev_month_sales'].isnull().all():
            prev_month_sales = 0
        else:
            prev_month_sales = prev_df['prev_month_sales'].fillna(0).iloc[0]
    except:
        prev_month_sales = 0

    # Rolling 3 aylık ortalama
    try:
        roll_q = f"""
            SELECT TO_CHAR(o.order_date, 'YYYY-MM') AS order_month, SUM(od.quantity) AS quantity
            FROM order_details od
            JOIN orders o ON od.order_id = o.order_id
            WHERE od.product_id = {input.product_id}
            AND o.order_date < '{order_date.strftime('%Y-%m-%d')}'
            GROUP BY order_month
            ORDER BY order_month DESC
            LIMIT 3
        """
        roll_df = pd.read_sql(roll_q, engine)
        sales_rolling_3 = roll_df['quantity'].mean() if not roll_df.empty else 0
    except:
        sales_rolling_3 = 0

    # Özellik vektörü
    try:
        data = np.array([[order_month_num, product_code, input.unit_price,
                          month_only, prev_month_sales, sales_rolling_3]])
        prediction = model.predict(data)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tahmin hatası: {str(e)}")

    return {
        "tahmin_edilen_satis_miktari": round(prediction, 2),
        "kullanilan_veri": {
            "order_month_num": order_month_num,
            "product_code": int(product_code),
            "unit_price": input.unit_price,
            "month_only": month_only,
            "prev_month_sales": prev_month_sales,
            "sales_rolling_3": round(sales_rolling_3, 2)
        }
    }
