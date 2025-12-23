from pydantic import BaseModel


class UIFilters(BaseModel):
    industry: str | None = None
    horizon_years: int = 5
