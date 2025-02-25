from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
import crud
from schemas import IoCCreate, IoCResponse, UserCreate, UserResponse
from typing import List
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from models import IoC, User  # Modelo de la base de datos
import pandas as pd
from fastapi.responses import Response
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm



router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

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
    if clientes != ['']:
        sql += " AND cliente = ANY(:clientes)"
        params["clientes"] = clientes

    # Ejecutar la consulta
    query = await db.execute(text(sql), params)
    iocs = query.fetchall()
    
    if not iocs:
        return {"message": "No hay datos para generar el reporte."}
    
    #Convertir resultados en un DataFrame
    df = pd.DataFrame(iocs, columns=[
        "Tipo", "Valor", "Cliente", "Categoría", 
        "Tecnología", "Incidente", "Criticidad", "Fecha"
    ])

    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date  # Extrae solo la fecha (sin la hora)

    #Crear gráficos
    buffer_bar, buffer_pie = BytesIO(), BytesIO()

    plt.figure(figsize=(6, 4))
    df.groupby("Fecha").size().plot(kind="bar", title="IoCs Detectados por Día", color="blue")
    plt.xlabel("Fecha")
    plt.ylabel("Cantidad de IoCs")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(buffer_bar, format="png")
    buffer_bar.seek(0)

    plt.figure(figsize=(4, 4))
    df["Criticidad"].value_counts().plot(kind="pie", autopct="%1.1f%%", title="Distribución de Criticidad", colors=["red", "yellow", "green"])
    plt.tight_layout()
    plt.savefig(buffer_pie, format="png")
    buffer_pie.seek(0)

    #Crear PDF con formato profesional
    buffer_pdf = BytesIO()
    doc = SimpleDocTemplate(buffer_pdf, pagesize=letter)
    elements = []

    logo_path = "static/logo.png"  # Ruta del logo
    styles = getSampleStyleSheet()

    #Encabezado y pie de página
    def header_footer(canvas, doc):
        canvas.saveState()
        
        # Barra superior azul
        canvas.setFillColor(colors.HexColor("#003366"))
        canvas.rect(0, doc.height + 80, doc.width + 40, 50, fill=True, stroke=False)

        # Insertar logo
        canvas.drawImage(logo_path, 20, doc.height + 85, width=80, height=40)

        # Footer
        canvas.setFillColor(colors.black)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(40, 20, "Reporte generado por Be:Sec - Confidencial")
        canvas.restoreState()

    #Agregar título e información
    elements.append(Paragraph("<b>Reporte de IoCs</b>", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Período: {start_date.date()} - {end_date.date()}", styles["Normal"]))
    elements.append(Paragraph(f"Clientes: {', '.join(clientes)}", styles["Normal"]))
    elements.append(Spacer(1, 24))

    #Insertar gráficos en el PDF
    elements.append(Paragraph("<b>IoCs Detectados por Día</b>", styles["Heading2"]))
    elements.append(Spacer(1, 6))
    elements.append(Image(buffer_bar, width=400, height=200))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("<b>Distribución de Criticidad</b>", styles["Heading2"]))
    elements.append(Spacer(1, 6))
    elements.append(Image(buffer_pie, width=300, height=200))
    elements.append(Spacer(1, 24))

    #Crear tabla con los datos
    table_data = [["Tipo", "Valor", "Cliente", "Categoría", "Tecnología", "Incidente", "Criticidad", "Fecha"]]
    for ioc in iocs:
        table_data.append(list(ioc))

    table = Table(table_data, colWidths=[75] * 8)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),  # Fondo azul en encabezado
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),  # Tamaño de letra más pequeño
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),  # Texto blanco
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(Paragraph("<b>Detalles de los IoCs</b>", styles["Heading2"]))
    elements.append(Spacer(1, 6))
    elements.append(table)

    #Construir PDF con encabezado y footer en todas las páginas
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)

    # Guardar y devolver PDF
    buffer_pdf.seek(0)

    return Response(
        content=buffer_pdf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Reporte_IoCs.pdf"}
    )

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    return await crud.register_user(user, db)

@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    return await crud.login_user(form_data, db)

@router.get("/user_token")
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    return await crud.get_current_user(token, db)