from fastapi import FastAPI
from routes import router
import models
from database import engine
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
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


#Añadir la ruta /api a la ruta por defecto
app.include_router(router, prefix="/api")
