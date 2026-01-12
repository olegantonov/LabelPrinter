"""
Configurações do sistema de impressão de etiquetas
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
    DEFAULT_PRINTER_PIMACO_A4: Optional[str] = None
    DEFAULT_PRINTER_ENVELOPE_DL: Optional[str] = None
    DEFAULT_PRINTER_ENVELOPE_C5: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()

# Criar diretórios se não existirem
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.LABELS_DIR, exist_ok=True)


# Dimensões das etiquetas em mm
LABEL_SIZES = {
    "thermal_60x30": {"width": 60, "height": 30, "name": "Térmica 60x30mm"},
    "thermal_100x80": {"width": 100, "height": 80, "name": "Térmica 100x80mm"},
    "pimaco_a4": {
        "width": 99.0,
        "height": 38.1,
        "name": "Pimaco A4 (38,1x99mm)",
        "labels_per_sheet": 14,
        "columns": 2,
        "rows": 7,
        "page_width": 210,
        "page_height": 297,
        "margin_top": 12.7,
        "margin_left": 6.35,
        "spacing_h": 3.0,
        "spacing_v": 0
    },
    "envelope_dl": {"width": 220, "height": 110, "name": "Envelope DL (110x220mm)"},
    "envelope_c5": {"width": 229, "height": 162, "name": "Envelope C5 (162x229mm)"}
}
