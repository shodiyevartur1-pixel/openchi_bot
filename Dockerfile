FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Kerakli tizim kutubxonalari (bazalar uchun)
RUN apt-get update && apt-get install -y gcc libpq-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Agar main.py papka ichida bo'lsa (masalan: bot/main.py), pastdagi qatorni o'zgartiring
# Agar main.py ildizda bo'lsa (requirements yonida), quyidagicha qoldiring:
CMD ["python", "bot/main.py"]
