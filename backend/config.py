"""
Configurações do sistema de impressão de etiquetas
Apenas etiquetas térmicas
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Configurações da aplicação"""

    # Banco de dados
    DATABASE_URL: str = "sqlite:///./labelprinter.db"

    # Servidor
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Diretórios
    UPLOAD_DIR: str = "./uploads"
    LABELS_DIR: str = "./generated_labels"

    # Impressoras padrão por tipo de etiqueta
    DEFAULT_PRINTER_THERMAL_60x30: Optional[str] = None
    DEFAULT_PRINTER_THERMAL_100x80: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()

# Criar diretórios se não existirem
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.LABELS_DIR, exist_ok=True)


# Dimensões das etiquetas em mm - APENAS TÉRMICAS
LABEL_SIZES = {
    "thermal_60x30": {"width": 60, "height": 30, "name": "Térmica 60x30mm"},
    "thermal_100x80": {"width": 100, "height": 80, "name": "Térmica 100x80mm"}
}
