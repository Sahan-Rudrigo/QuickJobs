from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from database import Base


class CVRecord(Base):
    """
    Tracks every CV version uploaded by a job seeker.
    Max 3 versions per phone — oldest is deleted when a 4th is uploaded.
    """
    __tablename__ = "cv_records"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    phone      = Column(String, nullable=False, index=True)
    s3_key     = Column(String, nullable=False)
    version    = Column(Integer, nullable=False)
    file_name  = Column(String, nullable=True)
    file_type  = Column(String, nullable=True)   # pdf | docx
    text_length = Column(Integer, default=0)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
