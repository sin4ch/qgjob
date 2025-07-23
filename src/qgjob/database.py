import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import Base
import redis
import logging

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/qgjob")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create database engine with connection validation
try:
    engine = create_engine(DATABASE_URL, echo=False)
    # Test database connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.fetchone()  # Ensure the query actually executes
    logging.info("Connected to PostgreSQL database successfully")
except Exception as e:
    logging.error(f"Failed to connect to PostgreSQL database at {DATABASE_URL}: {e}")
    logging.error("PostgreSQL is required for production. Please ensure PostgreSQL is running and accessible.")
    logging.error("Database connection string format: postgresql://username:password@host:port/database")
    raise RuntimeError(f"Database connection failed: {e}. PostgreSQL is required for production operation.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Connect to Redis - fail fast if not available
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    logging.info("Connected to Redis successfully")
except Exception as e:
    logging.error(f"Failed to connect to Redis at {REDIS_URL}: {e}")
    logging.error("Redis is required for production. Please ensure Redis is running and accessible.")
    logging.error("To start Redis locally: docker run -d -p 6379:6379 redis:alpine")
    raise RuntimeError(f"Redis connection failed: {e}. Redis is required for production operation.")

def create_tables():
    """Create database tables if they don't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("Database tables created/verified successfully")
    except Exception as e:
        logging.error(f"Failed to create database tables: {e}")
        logging.error("Please ensure the database exists and the user has proper permissions")
        raise RuntimeError(f"Database table creation failed: {e}")

def get_db():
    """Get database session with proper error handling"""
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logging.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


