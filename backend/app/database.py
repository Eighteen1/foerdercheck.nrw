from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
        # Add SSL mode if not already present
        if "?" not in DATABASE_URL:
            DATABASE_URL += "?sslmode=require"
            
        # Configure engine with appropriate settings for Supabase Session Pooler
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=300,    # Recycle connections after 5 minutes
            pool_size=5,         # Set a reasonable pool size
            max_overflow=10,     # Allow some overflow connections
            # These settings are optimized for Supabase Session Pooler
            connect_args={
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
                "application_name": "foerdercheck"  # Helps with monitoring
            }
        )
        
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to the database using Session Pooler")
            
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 