"""Admin portal metadata must never serialize server-side credentials."""

from app.api.routes.admin import ClientPortalResponse


def test_client_portal_response_discards_server_local_passwords() -> None:
    portal = ClientPortalResponse(
        id="client-1",
        name="Fixture investor",
        slug="fixture",
        description="Fixture",
        portal_url="https://portal.example.test",
        status="active",
        sector="Software",
        location="AU",
        documents=[],
        access_password="must-not-reach-the-browser",
    )

    payload = portal.model_dump() if hasattr(portal, "model_dump") else portal.dict()

    assert "access_password" not in payload
    assert "must-not-reach-the-browser" not in str(payload)
