from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class IoCRef(BaseModel):
    id: int
    tipo: str
    valor: str
    cliente: str
    categoria: str
    tecnologia_deteccion: str
    criticidad: str
    usuario_registro: str
    fecha_creacion: datetime

    class Config:
        orm_mode = True

class IncidenteRef(BaseModel):
    id: int
    nombre: str

    class Config:
        orm_mode = True

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

class IncidenteBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = ""
    cliente: str
    fecha_incidente: datetime
    usuario_creador: str

class IncidenteCreate(IncidenteBase):
    pass

class IncidenteResponse(IncidenteBase):
    id: int
    iocs: List[IoCRef] = []

    class Config:
        orm_mode = True

class IoCResponse(IoCBase):
    id: int
    incidentes: List[IncidenteRef] = []

    class Config:
        orm_mode = True


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
    enterprise: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    enterprise: str

class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: str
       
    class Config:
        from_attributes = True

