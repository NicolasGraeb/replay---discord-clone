from typing import Optional

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    """Dla SPA / różnych portów — odświeżanie bez polegania wyłącznie na ciasteczku."""
    refresh_token: Optional[str] = None
