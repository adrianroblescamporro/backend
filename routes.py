from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from database import get_db
import crud
from schemas import IoCCreate, IoCResponse, IncidenteCreate, IncidenteResponse, IoCUpdate, UserCreate, UserResponse, LoginRequest
from typing import List
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from models import IoC, User, Incidente, EnriquecimientoIoC  # Modelo de la base de datos
import pandas as pd
from fastapi.responses import Response, PlainTextResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ioc_enrichment.manager import enrich_ioc
import pyotp
import qrcode
import json


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

#Verificar token
async def verify_token(token: str = Depends(oauth2_scheme)):
    return await crud.verify_token_route(token)

#Obtener IoCs
@router.get("/iocs", response_model=List[IoCResponse], dependencies=[Depends(verify_token)])
async def read_iocs(db: AsyncSession = Depends(get_db)):
    return await crud.get_iocs(db)

#Crear nuevos IoCs
@router.post("/iocs", response_model=IoCResponse, dependencies=[Depends(verify_token)])
async def create_ioc(ioc: IoCCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_ioc(db, ioc)

#Actualizar IoC
@router.put("/iocs/{ioc_id}", response_model=IoCUpdate, dependencies=[Depends(verify_token)])
async def update_ioc(ioc_id: int, ioc_data: IoCUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(IoC).where(IoC.id == ioc_id)
    result = await db.execute(stmt)
    ioc = result.scalars().first()

    if not ioc:
        raise HTTPException(status_code=404, detail="IoC no encontrado")

    # Excluir el usuario_registro de la actualización
    update_data = ioc_data.dict(exclude_unset=True, exclude={"usuario_registro"})

    for key, value in update_data.items():
        setattr(ioc, key, value)

    await db.commit()
    await db.refresh(ioc)
    return ioc

#Eliminar IoC
@router.delete("/iocs/{ioc_id}", dependencies=[Depends(verify_token)])
async def delete_ioc(ioc_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(IoC).where(IoC.id == ioc_id)
    result = await db.execute(stmt)
    ioc = result.scalars().first()

    if not ioc:
        raise HTTPException(status_code=404, detail="IoC no encontrado")

    await db.delete(ioc)
    await db.commit()
    return {"message": "IoC eliminado correctamente"}

#Generar reportes en pdf
@router.get("/generate_report", dependencies=[Depends(verify_token)])
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

#Generar archivos edl
@router.get("/report/edl", response_class=PlainTextResponse, dependencies=[Depends(verify_token)])
async def generar_edl(tipo: str, cliente: str, db: AsyncSession = Depends(get_db)):
    stmt = select(IoC).where(IoC.tipo == tipo, IoC.cliente == cliente)
    result = await db.execute(stmt)
    iocs = result.scalars().all()

    edl_content = "\n".join(ioc.valor for ioc in iocs)

    return PlainTextResponse(content=edl_content, media_type="text/plain")

@router.post("/register", response_model=UserResponse, dependencies=[Depends(verify_token)])
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    return await crud.register_user(user, db)

@router.post("/login")
async def login_user(form_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await crud.login_user(form_data, db)

@router.get("/user_token")
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    return await crud.get_current_user(token, db)

@router.get("/mfa/qrcode/{username}")
async def get_mfa_qr(username: str, db: AsyncSession = Depends(get_db)):
    user = await db.execute(select(User).where(User.username == username))
    user = user.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA ya está activado")

    otp_auth_url = pyotp.totp.TOTP(user.mfa_secret).provisioning_uri(
        user.username, issuer_name="IoCManagement"
    )

    qr = qrcode.make(otp_auth_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    return Response(buffer.read(), media_type="image/png")

@router.post("/mfa/verify")
async def verify_mfa(form_data: OAuth2PasswordRequestForm=Depends(), db: AsyncSession = Depends(get_db)):
    return await crud.verify_mfa(form_data, db)

#Enriquecer IoCs
@router.get("/ioc/enrich/{ioc}", dependencies=[Depends(verify_token)])
async def enrich_ioc_endpoint(ioc: str, db: AsyncSession = Depends(get_db)):
    #Buscar si ya está enriquecido
    result = await db.execute(
        select(EnriquecimientoIoC).where(EnriquecimientoIoC.valor_ioc == ioc)
    )
    cached = result.scalar_one_or_none()

    if cached:
        #Si lo está, devolverlo directamente
        return json.loads(cached.datos_json)

    #Enriquecer con los analizadores
    enriched = await enrich_ioc(ioc)

    #Serializar y guardar el resultado en la base de datos
    datos_json = json.dumps([r.model_dump() for r in enriched], default=str)

    nuevo = EnriquecimientoIoC(
        valor_ioc=ioc,
        datos_json=datos_json,
        fecha_enriquecimiento=datetime.utcnow()
    )
    db.add(nuevo)
    await db.commit()

    #Devolver el resultado enriquecido
    return [r.model_dump() for r in enriched]

# Crear nuevo incidente
@router.post("/incidentes", response_model=IncidenteResponse, dependencies=[Depends(verify_token)])
async def crear_incidente(incidente: IncidenteCreate, db: AsyncSession = Depends(get_db)):
    nuevo_incidente = Incidente(**incidente.dict())
    db.add(nuevo_incidente)
    await db.commit()
    await db.refresh(nuevo_incidente)
    return nuevo_incidente

# Asociar IoC a incidente
@router.post("/incidentes/{incidente_id}/add_ioc/{ioc_id}", dependencies=[Depends(verify_token)])
async def asociar_ioc_a_incidente(incidente_id: int, ioc_id: int, db: AsyncSession = Depends(get_db)):
    incidente = await db.get(Incidente, incidente_id)
    ioc = await db.get(IoC, ioc_id)

    if not incidente or not ioc:
        raise HTTPException(status_code=404, detail="IoC o Incidente no encontrado")

    if ioc not in incidente.iocs:
        incidente.iocs.append(ioc)
        await db.commit()

    return {"message": f"IoC {ioc_id} asociado al incidente {incidente_id}"}

#Eliminar IoC asociado a un incidente
@router.delete("/incidentes/{incidente_id}/remove_ioc/{ioc_id}", dependencies=[Depends(verify_token)])
async def remove_ioc_from_incidente(
    incidente_id: int,
    ioc_id: int,
    db: AsyncSession = Depends(get_db)
):
    incidente = await db.get(Incidente, incidente_id)
    ioc = await db.get(IoC, ioc_id)

    if not incidente or not ioc:
        raise HTTPException(status_code=404, detail="Incidente o IoC no encontrado")

    if ioc not in incidente.iocs:
        raise HTTPException(status_code=400, detail="El IoC no está asociado a este incidente")

    incidente.iocs.remove(ioc)
    await db.commit()

    return {"message": "IoC desasociado correctamente del incidente"}

# Obtener todos los incidentes con sus IoCs
@router.get("/incidentes", response_model=List[IncidenteResponse], dependencies=[Depends(verify_token)])
async def obtener_incidentes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Incidente)
        .options(
            selectinload(Incidente.iocs).selectinload(IoC.incidentes)
        )
    )
    incidentes = result.scalars().all()
    return incidentes

# Obtener los IoCs de un incidente
@router.get("/incidentes/{incidente_id}/iocs", response_model=List[IoCResponse], dependencies=[Depends(verify_token)])
async def obtener_iocs_de_incidente(incidente_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Incidente)
        .where(Incidente.id == incidente_id)
        .options(selectinload(Incidente.iocs).selectinload(IoC.incidentes))
    )
    result = await db.execute(stmt)
    incidente = result.scalars().first()

    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    return incidente.iocs

#Obtener los incidentes de un IoC
@router.get("/iocs/{ioc_id}/incidentes", response_model=List[IncidenteResponse], dependencies=[Depends(verify_token)])
async def obtener_incidentes_de_ioc(ioc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(IoC)
        .where(IoC.id == ioc_id)
        .options(
            selectinload(IoC.incidentes).selectinload(Incidente.iocs)  # 👈 Clave aquí
        )
    )
    ioc = result.scalars().first()

    if not ioc:
        raise HTTPException(status_code=404, detail="IoC no encontrado")

    return ioc.incidentes