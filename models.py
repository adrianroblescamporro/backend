from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

#Definición de clase IoC en función de los campos de la base de datos
class IoC(Base):
    __tablename__ = "iocs"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False)
    valor = Column(Text, unique=True, nullable=False)
    estado = Column(String(20), nullable=False)
    fecha_creacion = Column(TIMESTAMP, server_default=func.now())
