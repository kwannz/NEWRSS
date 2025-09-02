"""
Legacy auth module - redirects to enhanced security module
This file maintained for backward compatibility
"""
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    pwd_context,
    settings
)

# Legacy algorithm constant for backward compatibility
ALGORITHM = settings.JWT_ALGORITHM

# Warn about deprecated usage
import warnings
warnings.warn(
    "app.core.auth is deprecated. Use app.core.security instead.",
    DeprecationWarning,
    stacklevel=2
)