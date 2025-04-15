from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# If DATABASE_URL is not set, use SQLite (for local development)
if not DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./foerdercheck.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    # For PostgreSQL (production)
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 