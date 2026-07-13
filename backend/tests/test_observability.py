"""Error tracking must retain diagnostics without exporting investor secrets."""

from app.core.observability import scrub_error_event, scrub_transaction_event


def test_error_tracking_redacts_request_credentials_and_personal_data() -> None:
    event = {
        "user": {"email": "investor@example.com", "id": "investor-1"},
        "request": {
            "headers": {
                "Authorization": "Bearer secret",
                "Cookie": "session=secret",
                "X-API-Key": "secret",
                "X-Request-ID": "safe-correlation-id",
            },
            "query_string": "email=investor@example.com",
            "data": {"password": "secret"},
            "url": "https://research.example/api/books?email=investor@example.com#token=secret",
        },
    }

    scrubbed = scrub_error_event(event, {})

    assert "user" not in scrubbed
    assert scrubbed["request"]["headers"]["Authorization"] == "[Filtered]"
    assert scrubbed["request"]["headers"]["Cookie"] == "[Filtered]"
    assert scrubbed["request"]["headers"]["X-API-Key"] == "[Filtered]"
    assert scrubbed["request"]["headers"]["X-Request-ID"] == "safe-correlation-id"
    assert scrubbed["request"]["query_string"] == "[Filtered]"
    assert scrubbed["request"]["data"] == "[Filtered]"
    assert scrubbed["request"]["url"] == "https://research.example/api/books"


def test_transaction_tracking_strips_request_values_and_span_payloads() -> None:
    event = {
        "user": {"email": "investor@example.com"},
        "transaction": "/api/universe/company/AAA?account=investor-1",
        "request": {
            "url": "https://research.example/api/universe/company/AAA?account=investor-1",
            "query_string": "account=investor-1",
        },
        "extra": {"email": "investor@example.com"},
        "spans": [
            {
                "op": "db.sql.query",
                "description": "SELECT * FROM accounts WHERE email = 'investor@example.com'",
                "data": {"db.params": ["investor@example.com"]},
            }
        ],
    }

    scrubbed = scrub_transaction_event(event, {})

    assert "user" not in scrubbed
    assert "extra" not in scrubbed
    assert scrubbed["transaction"] == "/api/universe/company/AAA"
    assert scrubbed["request"]["url"] == "https://research.example/api/universe/company/AAA"
    assert scrubbed["request"]["query_string"] == "[Filtered]"
    assert scrubbed["spans"] == [{"op": "db.sql.query"}]
