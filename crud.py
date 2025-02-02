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
    new_ioc = IoC(**ioc_data.dict())
    db.add(new_ioc)
    await db.commit()
    await db.refresh(new_ioc)
    return new_ioc
