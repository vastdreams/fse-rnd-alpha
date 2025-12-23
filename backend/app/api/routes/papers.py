"""
Papers API Routes

Serves research papers and methodology documentation.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pathlib import Path

router = APIRouter()

# Path to papers directory
# In Docker container, papers are mounted at /app/papers
# Try mounted path first, then fallback to relative path for local development
if Path("/app/papers").exists():
    PAPERS_DIR = Path("/app/papers")
else:
    # Local development: From backend/app/api/routes/papers.py -> routes -> api -> app -> backend -> project root -> papers
    PAPERS_DIR = Path(__file__).parent.parent.parent.parent.parent / "papers"


@router.get("/list")
async def list_papers():
    """List all available papers."""
    papers = []
    if PAPERS_DIR.exists():
        for file in PAPERS_DIR.glob("*.md"):
            papers.append({
                "id": file.stem,
                "title": file.stem.replace("_", " ").title(),
                "filename": file.name
            })
    return {"papers": papers}


@router.get("/{paper_id}", response_class=PlainTextResponse)
async def get_paper(paper_id: str):
    """Get a specific paper by ID."""
    # Map paper IDs to filenames
    paper_map = {
        "paper-1": "paper_1_rd_returns.md",
        "paper-2": "paper_2_industry_analysis.md",
        "paper-3": "paper_3_multifactor.md",
        "paper-4": "paper_4_fundamental.md",
        "methodology": "METHODOLOGY.md",
    }
    
    filename = paper_map.get(paper_id)
    if not filename:
        # Try direct filename match
        filename = f"{paper_id}.md"
    
    file_path = PAPERS_DIR / filename
    
    if not file_path.exists():
        return PlainTextResponse("Paper not found", status_code=404)
    
    return PlainTextResponse(file_path.read_text())

