"""Lightweight HTTP router for easy, modular API registration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


RouteHandler = Callable[[Any, Dict[str, str]], None]


@dataclass
class Route:
    method: str
    pattern: re.Pattern[str]
    handler: RouteHandler
    require_auth: bool = True


class Router:
    """Minimal Express-style router supporting path params like `/api/effects/:name`."""

    def __init__(self) -> None:
        self._routes: List[Route] = []

    def add(
        self,
        method: str,
        path: str,
        handler: RouteHandler,
        *,
        require_auth: bool = True,
    ) -> None:
        escaped = re.escape(path)
        regex_str = re.sub(r"\\?:([a-zA-Z_][a-zA-Z0-9_]*)", r"(?P<\1>[^/]+)", escaped)
        pattern = re.compile(f"^{regex_str}$")
        self._routes.append(
            Route(
                method=method.upper(),
                pattern=pattern,
                handler=handler,
                require_auth=require_auth,
            )
        )

    def get(self, path: str, *, require_auth: bool = True):
        def decorator(fn: RouteHandler) -> RouteHandler:
            self.add("GET", path, fn, require_auth=require_auth)
            return fn

        return decorator

    def post(self, path: str, *, require_auth: bool = True):
        def decorator(fn: RouteHandler) -> RouteHandler:
            self.add("POST", path, fn, require_auth=require_auth)
            return fn

        return decorator

    def put(self, path: str, *, require_auth: bool = True):
        def decorator(fn: RouteHandler) -> RouteHandler:
            self.add("PUT", path, fn, require_auth=require_auth)
            return fn

        return decorator

    def delete(self, path: str, *, require_auth: bool = True):
        def decorator(fn: RouteHandler) -> RouteHandler:
            self.add("DELETE", path, fn, require_auth=require_auth)
            return fn

        return decorator

    def match(
        self, method: str, path: str
    ) -> Optional[Tuple[Route, Dict[str, str]]]:
        upper_method = method.upper()
        for route in self._routes:
            if route.method != upper_method:
                continue
            match = route.pattern.match(path)
            if match:
                return route, match.groupdict()
        return None
