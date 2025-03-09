from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import IoC, User
from schemas import IoCCreate, UserCreate, UserResponse
from security import get_password_hash, verify_password, create_access_token, decode_access_token
from fastapi.security import OAuth2PasswordRequestForm


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

async def register_user(user: UserCreate, db: AsyncSession):
    # Verificar si el usuario ya existe
    stmt = select(User).where(User.username == user.username)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password, role=user.role)
    
    db.add(new_user)
    await db.commit()
    return new_user

async def login_user(form_data: OAuth2PasswordRequestForm, db: AsyncSession):
    stmt = select(User).where(User.username == form_data.username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

async def get_current_user(token: str, db: AsyncSession):
    payload = decode_access_token(token)
    user = await db.execute(User.select().where(User.username == payload["sub"]))
    return user.scalars().first()
