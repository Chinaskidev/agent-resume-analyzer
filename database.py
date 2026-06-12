from sqlalchemy import Float, create_engine, Column, String, Integer, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from dotenv import load_dotenv

# 🔹 Cargar variables de entorno
load_dotenv()

# Obtener la URL de PostgreSQL desde Railway
DATABASE_URL = os.getenv("DATABASE_URL")

# Verificar que DATABASE_URL se cargó correctamente
if not DATABASE_URL:
    raise ValueError("ERROR: La variable de entorno DATABASE_URL no está configurada correctamente.")


# Configurar SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

#Modelo Cliente
class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True, nullable=False)

    trabajos = relationship("Trabajo", back_populates="cliente", cascade="all, delete")

#Modelo Trabajo
class Trabajo(Base):
    __tablename__ = "tipos_de_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)

    cliente = relationship("Cliente", back_populates="trabajos")
    habilidades = relationship("Habilidad", back_populates="trabajo", cascade="all, delete")
    funciones = relationship("Funcion", back_populates="trabajo", cascade="all, delete")
    perfil = relationship("Perfil", back_populates="trabajo", cascade="all, delete")
    analisis = relationship("Analisis", back_populates="trabajo", cascade="all, delete")

#Modelo Funciones del Trabajo
class Funcion(Base):
    __tablename__ = "funciones_del_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True, nullable=False)
    trabajo_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    trabajo = relationship("Trabajo", back_populates="funciones")

#Modelo Perfil del Trabajo
class Perfil(Base):
    __tablename__ = "perfil_del_trabajador"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    trabajo_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    trabajo = relationship("Trabajo", back_populates="perfil")

#Modelo Habilidades
class Habilidad(Base):
    __tablename__ = "habilidades"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    trabajo_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    trabajo = relationship("Trabajo", back_populates="habilidades")

#Modelo Analisis (historial de CVs analizados)
class Analisis(Base):
    __tablename__ = "analisis"
    id = Column(Integer, primary_key=True, index=True)
    nombre_del_candidato = Column(String, nullable=True)
    archivo = Column(String, nullable=False)
    titulo_trabajo = Column(String, nullable=False)
    match_score = Column(Float, nullable=False)   # puntaje final hibrido 0-10
    raw_score = Column(Float, nullable=False)     # coseno original 0-1, para recalibrar con datos reales
    puntaje_llm = Column(Float, nullable=True)    # puntuacion 0-10 que dio el LLM (None si no se pudo parsear)
    decision = Column(String, nullable=False)
    feedback = Column(String, nullable=False)
    creado_en = Column(DateTime, server_default=func.now())
    trabajo_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    trabajo = relationship("Trabajo", back_populates="analisis")

#Crear las tablas en PostgreSQL
def crear_tablas():
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("¡Tablas creadas correctamente!")

if __name__ == "__main__":
    crear_tablas()
