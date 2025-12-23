from pydantic import BaseModel


class CompanyDTO(BaseModel):
    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
