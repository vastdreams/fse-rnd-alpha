"""
PATH: backend/app/api/routes/subscribe/__init__.py
PURPOSE: Assembles subscribe sub-routers and re-exports public helpers
"""

from fastapi import APIRouter
from app.api.routes.subscribe.endpoints import router as _endpoints

router = APIRouter()
router.include_router(_endpoints)

# Re-export functions used by other modules (donations, admin)
from app.api.routes.subscribe.tokens import (  # noqa: E402, F401
    generate_unsubscribe_token,
    verify_unsubscribe_token,
    get_unsubscribe_url,
)
from app.api.routes.subscribe.helpers import (  # noqa: E402, F401
    add_subscriber_to_db,
    get_all_subscribers,
)
from app.api.routes.subscribe.email import send_thank_you_email  # noqa: E402, F401
