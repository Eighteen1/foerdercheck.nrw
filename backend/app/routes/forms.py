from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import uuid
from ..database import get_db
from .. import models, schemas
from ..auth import get_current_user

router = APIRouter()

# Form routes
@router.post("/api/forms/{form_type}", response_model=schemas.Form)
async def create_form(
    form_type: str,
    form_data: schemas.FormCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    form = models.Form(
        user_id=current_user.id,
        form_type=form_type,
        data=form_data.data,
        progress=form_data.progress
    )
    db.add(form)
    db.commit()
    db.refresh(form)
    return form

@router.get("/api/forms/{form_type}", response_model=schemas.Form)
async def get_form(
    form_type: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    form = db.query(models.Form).filter(
        models.Form.user_id == current_user.id,
        models.Form.form_type == form_type
    ).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form

@router.put("/api/forms/{form_type}", response_model=schemas.Form)
async def update_form(
    form_type: str,
    form_data: schemas.FormUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    form = db.query(models.Form).filter(
        models.Form.user_id == current_user.id,
        models.Form.form_type == form_type
    ).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    form.data = form_data.data
    form.progress = form_data.progress
    form.is_completed = form_data.is_completed
    form.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(form)
    return form

# Document routes
@router.post("/api/documents", response_model=schemas.Document)
async def upload_document(
    file: UploadFile = File(...),
    form_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Create unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Save file
    file_path = f"uploads/{current_user.id}/{unique_filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Create document record
    document = models.Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_type=file_extension[1:],
        file_size=len(content)
    )
    
    # Link to form if form_type is provided
    if form_type:
        form = db.query(models.Form).filter(
            models.Form.user_id == current_user.id,
            models.Form.form_type == form_type
        ).first()
        if form:
            document.form_id = form.id
    
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

@router.get("/api/documents", response_model=List[schemas.Document])
async def get_documents(
    form_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Document).filter(models.Document.user_id == current_user.id)
    
    if form_type:
        form = db.query(models.Form).filter(
            models.Form.user_id == current_user.id,
            models.Form.form_type == form_type
        ).first()
        if form:
            query = query.filter(models.Document.form_id == form.id)
    
    return query.all()

@router.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Delete record
    db.delete(document)
    db.commit()
    return {"message": "Document deleted successfully"} 