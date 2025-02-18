from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import IoC
from schemas import IoCCreate

#Función para obtener IoCs
async def get_iocs(db: AsyncSession):
    result = await db.execute(select(IoC))
    return result.scalars().all()

#Función para crear IoCs
async def create_ioc(db: AsyncSession, ioc_data: IoCCreate):
    # Verificar si el IoC ya existe en la base de datos
    stmt = select(IoC).where(IoC.valor == ioc_data.valor)
    result = await db.execute(stmt)
    existing_ioc = result.scalars().first()

    if existing_ioc:
        raise HTTPException(status_code=400, detail="El IoC ya existe en la base de datos.")
    
    new_ioc = IoC(**ioc_data.dict())
    db.add(new_ioc)
    await db.commit()
    await db.refresh(new_ioc)
    return new_ioc
