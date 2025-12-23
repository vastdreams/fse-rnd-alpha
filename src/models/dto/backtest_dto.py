from pydantic import BaseModel


class BacktestSpecDTO(BaseModel):
    id: str | None = None
    universe: list[str]
    start_year: int
    end_year: int
    horizons: list[int]


class BacktestResultDTO(BaseModel):
    formation_year: int
    horizon_years: int
    industry: str
    bucket: str
    mean_ret: float
    t_stat: float | None = None
    n: int
    stderr: float | None = None
