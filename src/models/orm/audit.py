from sqlalchemy import Column, String, DateTime
from .base_model import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    context = Column(String, nullable=True)  # JSON as string or similar
    at = Column(DateTime(timezone=True), nullable=False)
