from sqlalchemy import Column, Integer, Enum, String, Text, Boolean, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

#Definición de clase IoC en función de los campos de la base de datos
class IoC(Base):
    __tablename__ = "iocs"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False)
    valor = Column(Text, unique=True, nullable=False)
    cliente = Column(String(20), index=True)  # Cliente en el que se detecta el IoC
    categoria = Column(String(50), index=True)  # Phishing, ransomware, etc.
    tecnologia_deteccion = Column(String(20), index=True)  # NDR,XDR, Correo...
    pertenece_a_incidente = Column(Boolean, default=False)  # ¿Pertenece a un incidente?
    criticidad = Column(String(20), index=True)  # Crítica, Alta, Media, Baja
    usuario_registro = Column(String(20), index=True)
    fecha_creacion = Column(TIMESTAMP, server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum("admin", "analista", "lector", name="user_roles"), nullable=False)
    mfa_secret = Column(String, nullable=True)  # Clave MFA
    mfa_enabled = Column(Boolean, default=False)  # Indica si MFA está activo