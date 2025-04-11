import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error
import joblib
from dotenv import load_dotenv
import os

# Ortam değişkenlerini yükle
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Veritabanı bağlantısı
engine = create_engine(DATABASE_URL)

# Veritabanı bağlantısı
def load_data():
    query = """
    SELECT o.order_date, od.product_id, od.quantity, od.unit_price,
           c.country, p.product_name
    FROM order_details od
    JOIN orders o ON od.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN products p ON od.product_id = p.product_id
    """
    df = pd.read_sql(query, engine)
    return df

# Özellik mühendisliği
def create_features(df):
    df["sales"] = df["quantity"] * df["unit_price"]
    df["sales"] = df["sales"].fillna(0).apply(lambda x: max(x, 0))

    df["order_date"] = pd.to_datetime(df["order_date"])
    df["month"] = df["order_date"].dt.month
    df["year"] = df["order_date"].dt.year
    df["day_of_week"] = df["order_date"].dt.dayofweek

    def get_season(month):
        if month in [3, 4, 5]:
            return 1
        elif month in [6, 7, 8]:
            return 2
        elif month in [9, 10, 11]:
            return 3
        else:
            return 4
    df["season"] = df["month"].apply(get_season)

    df["country_code"] = df["country"].astype("category").cat.codes
    df["product_code"] = df["product_name"].astype("category").cat.codes
    df["avg_price"] = df.groupby("product_code")["unit_price"].transform("mean")
    df["log_sales"] = np.log1p(df["sales"])

    df = df.dropna()

    features = [
        "month", "year", "day_of_week", "season",
        "country_code", "product_code",
        "quantity", "unit_price", "avg_price",
        "sales"  # veya "log_sales"
    ]

    return df[features]

# Model eğitimi ve korelasyon analizi
def train_model(df):
    print("\n=== Korelasyon Matrisi ===")
    print(df.corr(numeric_only=True)['sales'].sort_values(ascending=False))

    X = df.drop(columns=["sales"])
    y = df["sales"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"\nTest R2: {r2:.4f}, RMSE: {rmse:.2f}")
    
    
    return model, r2, rmse

# Modeli kaydet
def save_model(model, filename="rf_model.pkl"):
    joblib.dump(model, filename)

# Ana akış
def main():
    raw_df = load_data()
    df = create_features(raw_df)
    model, r2, rmse = train_model(df)  # bu satır artık tamam
    save_model(model)
    return {"R2": round(r2, 4), "RMSE": round(rmse, 2), "status": "Model başarıyla kaydedildi."}

if __name__ == "__main__":
    main()
