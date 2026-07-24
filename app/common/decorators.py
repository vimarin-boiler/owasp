from __future__ import annotations

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from flask import flash, redirect, request, url_for
from flask_login import current_user

P = ParamSpec("P")
R = TypeVar("R")


def password_change_required(view: Callable[P, R]) -> Callable[P, R]:
    @wraps(view)
    def wrapped(*args: P.args, **kwargs: P.kwargs):
        if current_user.is_authenticated and current_user.must_change_password:
            flash("Debes cambiar tu contraseña antes de continuar.", "warning")
            return redirect(url_for("auth.change_password", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped
