from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=1800, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase):
    pass

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()
