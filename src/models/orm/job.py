from sqlalchemy import Column, String, DateTime
from .base_model import BaseModel


class Job(BaseModel):
    __tablename__ = "jobs"

    status = Column(String, nullable=False)
    params = Column(String, nullable=False)  # could be JSON string
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
