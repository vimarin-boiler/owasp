from __future__ import annotations

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from app.common.validators import validate_password


class UserCreateForm(FlaskForm):
    display_name = StringField("Nombre", validators=[DataRequired(), Length(max=160)])
    email = EmailField("Correo electrónico", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Contraseña inicial", validators=[DataRequired(), Length(max=256)])
    role_ids = SelectMultipleField("Roles", coerce=int, validators=[DataRequired()])
    is_active = BooleanField("Usuario activo", default=True)
    must_change_password = BooleanField("Exigir cambio de contraseña", default=True)
    submit = SubmitField("Crear usuario")

    def validate_password(self, field) -> None:
        result = validate_password(field.data, current_app.config.get("PASSWORD_MIN_LENGTH", 12))
        if not result.valid:
            raise ValidationError(" ".join(result.errors))


class UserEditForm(FlaskForm):
    display_name = StringField("Nombre", validators=[DataRequired(), Length(max=160)])
    email = EmailField("Correo electrónico", validators=[DataRequired(), Email(), Length(max=254)])
    role_ids = SelectMultipleField("Roles", coerce=int, validators=[DataRequired()])
    is_active = BooleanField("Usuario activo")
    must_change_password = BooleanField("Exigir cambio de contraseña")
    submit = SubmitField("Guardar cambios")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Nueva contraseña temporal", validators=[DataRequired(), Length(max=256)])
    submit = SubmitField("Restablecer contraseña")

    def validate_password(self, field) -> None:
        result = validate_password(field.data, current_app.config.get("PASSWORD_MIN_LENGTH", 12))
        if not result.valid:
            raise ValidationError(" ".join(result.errors))


class OrganizationForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=180)])
    legal_name = StringField("Razón social", validators=[Optional(), Length(max=240)])
    tax_identifier = StringField("Identificador tributario", validators=[Optional(), Length(max=80)])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=3000)])
    is_active = BooleanField("Organización activa", default=True)
    submit = SubmitField("Guardar organización")
