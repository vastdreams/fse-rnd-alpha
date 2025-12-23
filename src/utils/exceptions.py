class ApiError(Exception):
    """Base API error class."""
    pass


class ValidationError(ApiError):
    """Raised when input validation fails."""
    pass
