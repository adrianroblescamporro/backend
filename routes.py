from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
import crud
from schemas import IoCCreate, IoCResponse
from typing import List
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from models import IoC  # Modelo de la base de datos
import pandas as pd
from fastapi.responses import Response

router = APIRouter()

#Obtener IoCs
@router.get("/iocs", response_model=List[IoCResponse])
async def read_iocs(db: AsyncSession = Depends(get_db)):
    return await crud.get_iocs(db)

#Crear nuevos IoCs
@router.post("/iocs", response_model=IoCResponse)
async def create_ioc(ioc: IoCCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_ioc(db, ioc)

#Generar reportes en pdf
@router.get("/generate_report")
async def generate_report(start_date: str, end_date: str, clientes: str, db: AsyncSession = Depends(get_db)):
    """
    Genera un reporte en PDF de los IoCs dentro del período de tiempo y clientes seleccionados.
    """
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    clientes = clientes.split(",")  # Lista de clientes seleccionados

    # Consultar IoCs dentro del rango de fechas y clientes
    # Construcción dinámica de la consulta
    sql = """
        SELECT tipo, valor, cliente, categoria, tecnologia_deteccion, 
            pertenece_a_incidente, criticidad, fecha_creacion
        FROM iocs
        WHERE fecha_creacion BETWEEN :start_date AND :end_date
    """

    params = {"start_date": start_date, "end_date": end_date}

    # Si hay clientes, agregar el filtro correctamente
    if clientes:
        sql += " AND cliente = ANY(:clientes)"
        params["clientes"] = clientes

    # Ejecutar la consulta
    query = await db.execute(text(sql), params)
    iocs = query.fetchall()
    
    if not iocs:
        return {"message": "No hay datos para generar el reporte."}
    
    # Convertir resultados en un DataFrame
    df = pd.DataFrame(iocs, columns=["Tipo", "Valor", "Cliente", "Categoría", "Tecnología", "Incidente", "Criticidad", "Fecha"])

    # Crear gráficos
    plt.figure(figsize=(6, 4))
    df.groupby("Fecha").size().plot(kind="bar", title="IoCs Detectados por Día")
    plt.xlabel("Fecha")
    plt.ylabel("Cantidad de IoCs")
    buffer_bar = BytesIO()
    plt.savefig(buffer_bar, format="png")
    buffer_bar.seek(0)
    
    plt.figure(figsize=(4, 4))
    df["Criticidad"].value_counts().plot(kind="pie", autopct="%1.1f%%", title="Distribución de Criticidad")
    buffer_pie = BytesIO()
    plt.savefig(buffer_pie, format="png")
    buffer_pie.seek(0)
    
    # Crear PDF
    buffer_pdf = BytesIO()
    pdf = canvas.Canvas(buffer_pdf, pagesize=letter)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(30, 750, "Reporte de IoCs")
    pdf.drawString(30, 730, f"Período: {start_date.date()} - {end_date.date()}")
    pdf.drawString(30, 710, f"Clientes: {', '.join(clientes)}")
    
    # Agregar gráficos
    pdf.drawImage(ImageReader(buffer_bar), 50, 450, width=500, height=200)
    pdf.drawImage(ImageReader(buffer_pie), 100, 250, width=300, height=200)
    
    # Guardar PDF
    pdf.showPage()
    pdf.save()
    buffer_pdf.seek(0)
    
    return Response(
        content=buffer_pdf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Reporte_IoCs.pdf"}
    )
