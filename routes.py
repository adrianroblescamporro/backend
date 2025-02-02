from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
import crud
from schemas import IoCCreate, IoCResponse
from typing import List

router = APIRouter()

#Obtener IoCs
@router.get("/iocs", response_model=List[IoCResponse])
async def read_iocs(db: AsyncSession = Depends(get_db)):
    return await crud.get_iocs(db)

#Crear nuevos IoCs
@router.post("/iocs", response_model=IoCResponse)
async def create_ioc(ioc: IoCCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_ioc(db, ioc)
