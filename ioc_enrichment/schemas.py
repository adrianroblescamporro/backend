from pydantic import BaseModel
from typing import Any, Optional

class AnalyzerResult(BaseModel):
    source: str                # Nombre del servicio
    summary: Optional[str] = None     # Breve resumen para mostrar rápidamente
    full: Optional[dict] = {}  # Resultado completo crudo
    error: Optional[str] = None  # Si ocurrió algún error
