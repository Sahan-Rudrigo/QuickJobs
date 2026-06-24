from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CVRecordResponse(BaseModel):
    id: int
    phone: str
    s3_key: str
    version: int
    file_name: Optional[str]
    file_type: Optional[str]
    text_length: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class CVUploadResponse(BaseModel):
    status: str
    phone: str
    s3_key: str
    version: int
    text_length: int
    message: str
