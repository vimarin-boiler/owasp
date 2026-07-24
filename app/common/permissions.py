from __future__ import annotations

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from flask import abort
from flask_login import current_user

P = ParamSpec("P")
R = TypeVar("R")


def roles_required(*role_codes: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    required = set(role_codes)

    def decorator(view: Callable[P, R]) -> Callable[P, R]:
        @wraps(view)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.is_active or not any(
                current_user.has_role(code) for code in required
            ):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(view: Callable[P, R]) -> Callable[P, R]:
    return roles_required("admin")(view)
