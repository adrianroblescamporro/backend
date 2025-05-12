from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from models import IoC, User, Incidente
from schemas import IoCCreate, UserCreate, LoginRequest
from security import get_password_hash, verify_password, create_access_token, decode_access_token
from fastapi.security import OAuth2PasswordRequestForm
import pyotp
import ipaddress


#Función para obtener IoCs
async def get_iocs(db: AsyncSession):
    result = await db.execute(
        select(IoC).options(
            selectinload(IoC.incidentes).selectinload(Incidente.iocs)
        )
    )
    iocs = result.scalars().all()
    return iocs

#Función para crear IoCs
async def create_ioc(db: AsyncSession, ioc_data: IoCCreate):
    # Verificar si el IoC ya existe en la base de datos
    stmt = select(IoC).where(IoC.valor == ioc_data.valor)
    result = await db.execute(stmt)
    existing_ioc = result.scalars().first()

    if existing_ioc:
        raise HTTPException(status_code=400, detail="El IoC ya existe en la base de datos.")
    
    # Validar que si el tipo es IP, no sea privada
    if ioc_data.tipo.lower() == "ip":
        try:
            ip = ipaddress.ip_address(ioc_data.valor)
            if ip.is_private:
                raise HTTPException(status_code=400, detail="No se permiten direcciones IP privadas.")
        except ValueError:
            raise HTTPException(status_code=400, detail="El valor ingresado no es una IP válida.")
        
    new_ioc = IoC(**ioc_data.dict())
    db.add(new_ioc)
    await db.commit()
    await db.refresh(new_ioc)
    return new_ioc

async def register_user(user: UserCreate, db: AsyncSession):
    # Verificar si el usuario ya existe
    stmt = select(User).where(User.username == user.username)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    hashed_password = get_password_hash(user.password)
    # Generar clave MFA
    mfa_secret = pyotp.random_base32()
    new_user = User(username=user.username, hashed_password=hashed_password, role=user.role, mfa_secret=mfa_secret,mfa_enabled=False, enterprise=user.enterprise)
    
    db.add(new_user)
    await db.commit()
    return new_user

async def login_user(form_data: LoginRequest, db: AsyncSession):
    stmt = select(User).where(User.username == form_data.username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if not user.mfa_enabled:
        raise HTTPException(status_code=403, detail="Debe configurar MFA primero")

    # Verificar el código MFA
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(form_data.mfa_code):
        raise HTTPException(status_code=402, detail="Código MFA incorrecto")

    # Generar token
    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "enterprise": user.enterprise
    })

    # Devolver token + bandera de cambio de contraseña
    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": user.must_change_password
    }


async def get_current_user(token: str, db: AsyncSession):
    payload = decode_access_token(token)
    user = await db.execute(User.select().where(User.username == payload["sub"]))
    return user.scalars().first()

async def verify_mfa(form_data: OAuth2PasswordRequestForm, db: AsyncSession):
    user = await db.execute(select(User).where(User.username == form_data.username))
    user = user.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(form_data.password):
        raise HTTPException(status_code=401, detail="Código MFA incorrecto")

    user.mfa_enabled = True  # Ahora MFA está activado
    await db.commit()

    return {"message": "MFA activado correctamente"}

async def verify_token_route(token: str):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return payload

async def change_user_password(username: str, new_password: str, db: AsyncSession):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    user.hashed_password = get_password_hash(new_password)
    user.must_change_password = False  # Marcar que ya no es el primer login

    db.add(user)
    await db.commit()
    return {"message": "Contraseña actualizada correctamente"}