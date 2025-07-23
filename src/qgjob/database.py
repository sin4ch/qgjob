import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import redis

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/qgjob")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
