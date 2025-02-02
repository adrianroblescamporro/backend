from pydantic import BaseModel
from datetime import datetime

class IoCBase(BaseModel):
    tipo: str
    valor: str
    estado: str

class IoCCreate(IoCBase):
    pass

class IoCResponse(IoCBase):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True
