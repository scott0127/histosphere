"""Supabase JWT verification and request actor ownership rules."""

from dataclasses import dataclass
import hashlib
from time import monotonic

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings


@dataclass(frozen=True)
class AuthenticatedUser:
    """Minimal identity returned by Supabase Auth."""

    id: str
    email: str | None = None


@dataclass(frozen=True)
class AuthenticatedActor:
    """Verified request identity, or an explicit Admin-key override."""

    user_id: str | None
    is_admin: bool = False

    def resolve_user_id(self, requested_user_id: str | None = None) -> str:
        """Learner requests always use the JWT subject; Admin may select a test identity."""
        resolved = requested_user_id if self.is_admin else self.user_id
        if not resolved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user identity is required for this operation",
            )
        return resolved

    def require_owner(self, owner_user_id: str | None) -> None:
        """Reject cross-account reads and writes while allowing explicit Admin testing."""
        if self.is_admin:
            return
        if not owner_user_id or owner_user_id != self.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Resource belongs to another Auth user",
            )


class SupabaseJWTVerifier:
    """Validate bearer tokens through Supabase Auth's canonical user endpoint."""

    def __init__(self, settings: Settings, *, cache_ttl_seconds: float = 30.0) -> None:
        self.supabase_url = (settings.supabase_url or "").rstrip("/")
        self.api_key = settings.supabase_anon_key or settings.supabase_service_role_key or ""
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, AuthenticatedUser]] = {}

    async def verify(self, token: str) -> AuthenticatedUser:
        token = token.strip()
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        if not self.supabase_url or not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase Auth verification is not configured",
            )

        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        cached = self._cache.get(token_hash)
        now = monotonic()
        if cached and cached[0] > now:
            return cached[1]

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    f"{self.supabase_url}/auth/v1/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "apikey": self.api_key,
                    },
                )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase Auth verification is unavailable",
            ) from exc

        if response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired bearer token")
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase Auth verification failed",
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase Auth returned an invalid response",
            ) from exc

        user_id = str(payload.get("id") or "").strip()
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token has no user identity")

        user = AuthenticatedUser(id=user_id, email=payload.get("email"))
        self._cache[token_hash] = (now + self.cache_ttl_seconds, user)
        return user
