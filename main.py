from fastapi import FastAPI
from routes import router
import models
from database import engine
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from database import AsyncSessionLocal  # Asegúrate de importar tu session factory
from models import IoC 
from sqlalchemy import delete

app = FastAPI()
scheduler = AsyncIOScheduler()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes especificar "http://localhost:3000" si quieres restringir a esa URL
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos HTTP
    allow_headers=["*"],  # Permite todos los headers
)

#Al iniciar la aplicación sincronizar información con la base de datos
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# Tarea que se ejecuta al comienzo de cada mes
async def eliminar_iocs_antiguos():
    async with AsyncSessionLocal() as session:
        hace_tres_meses = datetime.utcnow() - timedelta(days=90)
        stmt = delete(IoC).where(IoC.fecha_creacion <= hace_tres_meses)
        await session.execute(stmt)
        await session.commit()
        print("Se han eliminado los IoCs antiguos.")

#Añadir la ruta /api a la ruta por defecto
app.include_router(router, prefix="/api")

# Añadir tarea programada de borrrado: a las 00:00 el día 1 de cada mes
scheduler.add_job(eliminar_iocs_antiguos, CronTrigger(day=1, hour=0, minute=0))
scheduler.start()