"""Input validators for auth and dataset."""


def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email)) if email else False


def validate_password(password: str) -> bool:
    """Validate password strength (min length, etc.)."""
    return len(password) >= 8 if password else False
