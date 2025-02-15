from pydantic import BaseModel
from datetime import datetime

class IoCBase(BaseModel):
    tipo: str
    valor: str
    cliente: str
    categoria: str
    tecnologia_deteccion: str
    pertenece_a_incidente: bool
    criticidad: str
    usuario_registro: str
    fecha_creacion: datetime

class IoCCreate(IoCBase):
    pass

class IoCResponse(IoCBase):
    id: int

    class Config:
        from_attributes = True
