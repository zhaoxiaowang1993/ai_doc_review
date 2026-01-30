from __future__ import annotations

from pathlib import Path
from typing import Iterable

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class SPAStaticFiles(StaticFiles):
    def __init__(
        self,
        *,
        directory: str | Path,
        index_file: str = "index.html",
        exclude_prefixes: Iterable[str] = ("/api", "/ws"),
        **kwargs,
    ) -> None:
        super().__init__(directory=directory, **kwargs)
        self._index_file = index_file
        self._exclude_prefixes = tuple(exclude_prefixes)

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if not self._should_fallback(scope=scope, path=path, exc=exc):
                raise
            return await super().get_response(self._index_file, scope)

    def _should_fallback(self, *, scope: Scope, path: str, exc: HTTPException) -> bool:
        if exc.status_code != 404:
            return False

        method = scope.get("method")
        if method not in ("GET", "HEAD"):
            return False

        request_path = scope.get("path", "")
        if any(request_path.startswith(prefix) for prefix in self._exclude_prefixes):
            return False

        normalized = path.lstrip("/")
        last_segment = normalized.rsplit("/", 1)[-1]
        if "." in last_segment:
            return False

        return True
