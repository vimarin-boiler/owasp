from __future__ import annotations

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.common.validators import validate_password


class LoginForm(FlaskForm):
    email = EmailField(
        "Correo electrónico",
        validators=[DataRequired(), Email(), Length(max=254)],
        render_kw={"autocomplete": "username"},
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(), Length(max=256)],
        render_kw={"autocomplete": "current-password"},
    )
    remember = BooleanField("Mantener sesión iniciada")
    submit = SubmitField("Ingresar")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Contraseña actual",
        validators=[DataRequired(), Length(max=256)],
        render_kw={"autocomplete": "current-password"},
    )
    new_password = PasswordField(
        "Nueva contraseña",
        validators=[DataRequired(), Length(max=256)],
        render_kw={"autocomplete": "new-password"},
    )
    confirm_password = PasswordField(
        "Confirmar nueva contraseña",
        validators=[DataRequired(), EqualTo("new_password", message="Las contraseñas no coinciden.")],
        render_kw={"autocomplete": "new-password"},
    )
    submit = SubmitField("Actualizar contraseña")

    def validate_new_password(self, field) -> None:
        result = validate_password(
            field.data, current_app.config.get("PASSWORD_MIN_LENGTH", 12)
        )
        if not result.valid:
            raise ValidationError(" ".join(result.errors))
