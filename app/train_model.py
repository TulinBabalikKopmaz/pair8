from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
import joblib
from dotenv import load_dotenv
import os

# Veritabanı bağlantısı
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

# SQLAlchemy modelleri
class Product(Base):
    __tablename__ = 'products'
    product_id = Column('product_id', Integer, primary_key=True)
    product_name = Column('product_name', String)
    unit_price = Column('unit_price', Float)

class Order(Base):
    __tablename__ = 'orders'
    order_id = Column('order_id', Integer, primary_key=True)
    order_date = Column('order_date', Date)

class OrderDetail(Base):
    __tablename__ = 'order_details'
    order_id = Column('order_id', Integer, ForeignKey('orders.order_id'), primary_key=True)
    product_id = Column('product_id', Integer, primary_key=True)
    quantity = Column('quantity', Integer)

def train_and_save_model():
    # Veri çekme
    products_df = pd.read_sql(session.query(Product).statement, engine)
    orders_df = pd.read_sql(session.query(Order).statement, engine)
    order_details_df = pd.read_sql(session.query(OrderDetail).statement, engine)

    # Veri ön işleme
    orders_df['order_date'] = pd.to_datetime(orders_df['order_date'])
    orders_df['order_month'] = orders_df['order_date'].dt.to_period('M').astype(str)

    merged = pd.merge(order_details_df, orders_df, on='order_id')
    merged = pd.merge(merged, products_df, on='product_id')
    merged = merged.dropna(subset=['order_date', 'quantity', 'unit_price'])

    monthly_sales = merged.groupby(['product_name', 'order_month']).agg({
        'quantity': 'sum',
        'unit_price': 'mean'
    }).reset_index().rename(columns={'quantity': 'total_quantity'})

    df = monthly_sales.copy()
    df['order_month'] = pd.to_datetime(df['order_month'])
    df = df.sort_values(['product_name', 'order_month'])
    df['product_code'] = df['product_name'].astype('category').cat.codes
    df['order_month_num'] = df['order_month'].dt.strftime('%Y%m').astype(int)
    df['month_only'] = df['order_month'].dt.month
    df['prev_month_sales'] = df.groupby('product_name')['total_quantity'].shift(1)
    df['sales_rolling_3'] = df.groupby('product_name')['total_quantity'].rolling(3).mean().shift(1).reset_index(0, drop=True)
    df = df.dropna(subset=['prev_month_sales', 'sales_rolling_3'])

    # Kodu eşle ve kaydet
    product_code_map = df[['product_name', 'product_code']].drop_duplicates()
    joblib.dump(dict(zip(product_code_map['product_name'], product_code_map['product_code'])), 'product_code_map.pkl')

    # Korelasyon
    print("\n=== Korelasyon Matrisi ===")
    print(df.corr(numeric_only=True)['total_quantity'].sort_values(ascending=False))

    # Model eğitimi
    X = df[['order_month_num', 'product_code', 'unit_price', 'month_only', 'prev_month_sales', 'sales_rolling_3']]
    y = df['total_quantity']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    joblib.dump(model, 'sales_model.pkl')
    print("Model başarıyla kaydedildi. R2:", r2, "RMSE:", rmse)

    return {
        "R2": round(r2, 4),
        "RMSE": round(rmse, 2),
        "status": "Model başarıyla eğitildi ve kaydedildi."
    }

if __name__ == "__main__":
    train_and_save_model()
