from sqlalchemy.orm import Session
from app.models.usuarios import Usuario

def crear_usuario(db: Session, nombre: str, numero_whatsapp: str):
    nuevo_usuario = Usuario(
        nombre=nombre,
        numero_whatsapp=numero_whatsapp
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

def obtener_usuario_por_numero(db: Session, numero_whatsapp: str):
    return db.query(Usuario).filter(Usuario.numero_whatsapp == numero_whatsapp).first()