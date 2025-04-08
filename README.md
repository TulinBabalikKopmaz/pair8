# pair8
# Satış Tahmin API - Docker ile Kurulum ve Kullanım Kılavuzu

Bu proje, FastAPI ile oluşturulmuş bir satış tahmin sistemidir. Uygulama bir makine öğrenmesi modeli kullanarak verilen ürün için tahmini satış miktarını hesaplar. Docker ortamında container olarak dağıtılabilir. Bu rehber, hiç Docker deneyimi olmayan bir geliştiricinin bile adım adım bu projeyi çalıştırmasını sağlar.

## ✨ Proje İçeriği

- FastAPI tabanlı REST API
- Linear Regression modeli (scikit-learn)
- PostgreSQL veritabanına bağlantı
- Tahmin için gerekli girişler: `product_id`, `unit_price`, `order_date`
- Swagger/OpenAPI arayüzü: `http://localhost:8000/docs`

## 🖥️ Sistem Gereksinimleri

- Windows 10/11 (64-bit)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) kurulmuş olmalı
- WSL2 veya Hyper-V destekli sistem
- 4 GB+ RAM önerilir

## 🧭 Adım Adım Kurulum Rehberi (Sıfırdan)

### 1. Docker Desktop Kurulumu

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) indir ve yükle.
2. Kurulum sırasında "WSL2 backend" aktif olduğundan emin ol.
3. Bilgisayarı yeniden başlat.
4. Terminali (CMD veya PowerShell) aç ve şunu yaz:
   ```bash
   docker --version
   ```
   Bu komut Docker'ın kurulu olup olmadığını kontrol eder.

### 2. Projeyi GitHub'dan Klonla

```bash
git clone https://github.com/kullaniciadi/satis-tahmin-api.git
cd satis-tahmin-api
```

### 3. .env Dosyasını Oluştur

Proje klasörünün kök dizininde bir `.env` dosyası oluştur ve aşağıdaki satırı içine yaz:

```env
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"
```

kodun açıklaması:

```env
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=your_host
POSTGRES_PORT=your_port
POSTGRES_DB=your_database
```

> ⚠️ **Dikkat:** Eğer bu proje tamamen Docker ortamında çalıştırılacaksa 
host yerine = host.docker.internal yaz
>

### 4. Gerekli Dosyaların Projede Olduğundan Emin Ol

Aşağıdaki dosyalar proje klasöründe yer almalı:

- `Dockerfile`
- `requirements.txt`
- `sales_model.pkl`
- `product_code_map.pkl`
- `app/` klasörü içinde `main.py` ve `train_model.py`

### 5. Docker İmajını Oluştur

```bash
docker build -t pair8 .
```
> Bu işlem birkaç dakika sürebilir. Başarılıysa `Successfully tagged pair8:latest` çıktısını alırsınız.

### 6. Modeli Eğit ve Kaydet (Opsiyonel - Eğer dosyalar yoksa)

```bash
docker run --env-file .env pair8 python app/train_model.py
```

> Bu adım `sales_model.pkl` ve `product_code_map.pkl` dosyalarını oluşturur.

### 7. API'yi Başlat

```bash
docker run -p 8000:8000 --env-file .env pair8
```

Tarayıcıdan `http://localhost:8000/docs` adresine giderek API'yi test edebilirsin.

## 🔍 Tahmin Nasıl Yapılır?

Swagger arayüzünde `POST /predict` endpoint'ine aşağıdaki örnek veriyi girin:
```json
{
  "product_id": 1,
  "unit_price": 15.99,
  "order_date": "2023-11-01"
}
```
Yanıt olarak tahmini satış miktarını ve kullanılan değişkenleri içeren bir JSON alırsınız.

## 🧠 Model Hakkında

Model tipi: **Linear Regression**

- Bağımsız değişkenler:
  - `order_month_num`: Sipariş tarihinin YYYYMM formatı
  - `product_code`: Ürün adına karşılık gelen sayısal kod
  - `unit_price`: Ürünün satış fiyatı
  - `month_only`: Sipariş ayı (1-12)
  - `prev_month_sales`: Önceki ayın satış miktarı
  - `sales_rolling_3`: Önceki 3 ayın ortalama satış miktarı
- Bağımlı değişken:
  - `total_quantity`: Tahmin edilmek istenen satış miktarı

## 📁 Proje Dosya Yapısı

```bash
satis-tahmin-api/
├── app/
│   ├── main.py             # FastAPI uygulaması
│   └── train_model.py      # Model eğitimi scripti
├── product_code_map.pkl    # Ürün isimlerine karşılık gelen kodlar
├── sales_model.pkl         # Eğitimli regresyon modeli
├── requirements.txt        # Gerekli Python paketleri
├── Dockerfile              # Docker yapılandırması
├── .env                    # Veritabanı bağlantısı (sen oluşturmalısın)
```

## 📜 Lisans

MIT

---

❤️ Destekleyenler için teşekkürler!
Bu proje seni ileri taşıdıysa GitHub’da yıldız bırakmayı unutma ⭐
