# Usa una imagen oficial de Python ligera como base
FROM python:3.10-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requerimientos primero para aprovechar el caché de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de tu proyecto al directorio de trabajo
# Esto asume que tu script está en una carpeta llamada 'scripts'
COPY ./scripts ./scripts
COPY credentials.json .

# Comando que se ejecutará cuando el contenedor inicie
CMD ["python", "scripts/sync_metrics.py"]
