"""Rate limiting (por IP) para endpoints sensibles vía slowapi."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Se usa con ``app.state.limiter`` en ``create_app``; el decorador lee el limiter
# del request app state.
limiter = Limiter(key_func=get_remote_address, default_limits=[])

__all__ = ["limiter"]
