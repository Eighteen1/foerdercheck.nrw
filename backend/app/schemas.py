from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class FormBase(BaseModel):
    form_type: str
    data: Dict[str, Any]
    progress: float = 0.0
    is_completed: bool = False

class FormCreate(FormBase):
    pass

class FormUpdate(FormBase):
    pass

class Form(FormBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    filename: str
    file_type: str
    file_size: int
    is_verified: bool = False

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: int
    user_id: int
    form_id: Optional[int] = None
    file_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True 