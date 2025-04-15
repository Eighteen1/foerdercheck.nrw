from sqlalchemy import create_engine
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
        # Add SSL mode and force IPv4 if not already present
        if "?" not in DATABASE_URL:
            DATABASE_URL += "?sslmode=require"
        if "hostaddr" not in DATABASE_URL:
            # Extract host from DATABASE_URL
            import re
            host_match = re.search(r'@([^:/]+)', DATABASE_URL)
            if host_match:
                host = host_match.group(1)
                # Force IPv4 by resolving host to IPv4 address
                import socket
                try:
                    ipv4 = socket.gethostbyname(host)
                    DATABASE_URL = DATABASE_URL.replace(f"@{host}", f"@{ipv4}")
                except socket.gaierror:
                    logger.warning(f"Could not resolve {host} to IPv4, using original host")

        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=300,    # Recycle connections after 5 minutes
            pool_size=5,         # Set a reasonable pool size
            max_overflow=10,     # Allow some overflow connections
            connect_args={
                "connect_timeout": 10,  # 10 second timeout
                "keepalives": 1,        # Enable keepalives
                "keepalives_idle": 30,  # 30 seconds before sending keepalive
                "keepalives_interval": 10,  # 10 seconds between keepalives
                "keepalives_count": 5    # 5 failed keepalives before closing
            }
        )
        
        # Test the connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
            logger.info("Successfully connected to the database")
            
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