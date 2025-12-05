# Usamos una imagen ligera de Python oficial
FROM python:3.11-slim

# Evitamos que Python genere archivos .pyc y forzamos la salida en consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo en la nube
WORKDIR /app

# Instalamos dependencias del sistema necesarias para leer PDFs
RUN apt-get update && apt-get install -y \
    build-essential \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos los requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código (app.py e index.html)
COPY . .

# Google Cloud espera que escuchemos en el puerto definido por la variable PORT (por defecto 8080)
ENV PORT=8080
EXPOSE 8080

# Comando de inicio profesional usando Gunicorn (Servidor de Producción)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app