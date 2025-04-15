from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import uuid
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Document check state
    document_check_state = Column(JSON, nullable=True)
    
    # Relationships
    forms = relationship("Form", back_populates="user")
    documents = relationship("Document", back_populates="user")
    
    def generate_auth_token(self):
        self.auth_token = str(uuid.uuid4())
        # Token expires in 30 minutes
        self.token_expires_at = datetime.utcnow() + timedelta(minutes=30)
        return self.auth_token

class Form(Base):
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    form_type = Column(String, index=True)  # e.g., "EINKOMMENSERKLÄRUNG", "SELBSTAUSKUNFT", "HAUPTANTRAG"
    data = Column(JSON)  # Store form data as JSON
    progress = Column(Float, default=0.0)  # Progress percentage (0-100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_completed = Column(Boolean, default=False)

    # Relationship
    user = relationship("User", back_populates="forms")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=True)  # Optional link to a form
    filename = Column(String)
    file_path = Column(String)  # Path to stored file
    file_type = Column(String)  # e.g., "pdf", "jpg"
    file_size = Column(Integer)  # Size in bytes
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="documents")
    form = relationship("Form") 