FROM python:3.11-slim

# Instalar dependencias do sistema
RUN apt-get update && apt-get install -y \
    cups-client \
    libcups2-dev \
    && rm -rf /var/lib/apt/lists/*

# Criar diretorio de trabalho
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo fonte
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Criar diretorios necessarios
RUN mkdir -p /app/backend/uploads /app/backend/generated_labels

# Expor porta
EXPOSE 8000

# Diretorio de trabalho do backend
WORKDIR /app/backend

# Comando de inicializacao
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
