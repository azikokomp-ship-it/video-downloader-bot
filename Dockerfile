FROM python:3.10-slim

# Tizimga kerakli vositalarni o'rnatish
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot kodlarini nusxalash
COPY . .

# Botni ishga tushirish
CMD ["python", "downloader_bot.py"]
