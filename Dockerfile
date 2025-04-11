# Bunu docker build komutuyla çalıştırırsan, pair8 adında bir image oluşur.
# Sonra docker run ile bu image’tan container başlatırsın.

# Dockerfile aslında bir image tarifidir
# Container, bir uygulamanın çalışan bir örneğidir ve genellikle tek bir görevi (işi) yapmak üzere tasarlanır

# Her biri ayrı container olur ve hepsi birlikte çalışır. Böylece:

# İzole çalışırlar (biri çökse diğerleri etkilenmez)

# Güncellemesi kolay olur (sadece o container rebuild edilir)

# Tek bir göreve odaklandığı için sistem daha modüler ve ölçeklenebilir olur

# Bu Dockerfile, Python tabanlı bir FastAPI uygulaması için bir çalışma ortamı oluşturur.

# Küçük boyutlu, bir Python imajı kullanılır (slim: gereksiz bileşenler içermez).
FROM python:3-slim

# Uygulamanın dış dünyaya açılacağı port belirtilir (FastAPI'nin çalışacağı port).
EXPOSE 8000

# Python’un .pyc uzantılı bytecode dosyalarını üretmesini engeller (gereksiz dosya oluşmaz).
ENV PYTHONDONTWRITEBYTECODE=1

# Python çıktılarını doğrudan terminale yazmasını sağlar (loglar daha okunabilir olur).
ENV PYTHONUNBUFFERED=1

# Bağımlılıkların tanımlı olduğu requirements.txt dosyasını konteynere kopyala.
COPY requirements.txt .

# Kopyalanan dosyadaki bağımlılıkları pip ile yükle.
RUN python -m pip install -r requirements.txt

# Konteyner içinde çalışma dizinini /app olarak ayarla.
WORKDIR /app

# Host’taki tüm proje dosyalarını konteynerin /app klasörüne kopyala.
COPY . /app

# Güvenlik amacıyla root kullanıcısı yerine özel bir kullanıcı oluşturulur (UID: 5678).
# Bu kullanıcıya /app klasörüne erişim izni verilir.
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app

# Artık bu kullanıcı ile işlemler yapılacak (root hakları yok → daha güvenli).
USER appuser

# Konteyner başlatıldığında çalışacak komut:
# FastAPI uygulamasını uvicorn ile başlatır. --reload sayesinde kod değişiklikleri otomatik algılanır.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

