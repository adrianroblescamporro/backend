from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class IoCBase(BaseModel):
    tipo: str
    valor: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9._\-/:]+$")
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

class IoCUpdate(BaseModel):
    tipo: Optional[str]
    valor: Optional[str]
    cliente: Optional[str]
    categoria: Optional[str]
    tecnologia_deteccion: Optional[str]
    pertenece_a_incidente: Optional[bool]
    criticidad: Optional[str]
    fecha_creacion: Optional[datetime]

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    

    class Config:
        from_attributes = True
