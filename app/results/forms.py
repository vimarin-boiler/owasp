from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, DecimalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class RecommendationForm(FlaskForm):
    dimension_ref = SelectField("Asociar a", choices=[], validators=[Optional()])
    title = StringField("Título", validators=[DataRequired(), Length(max=240)])
    description = TextAreaField("Descripción", validators=[DataRequired(), Length(max=12000)])
    risk = TextAreaField("Riesgo asociado", validators=[Optional(), Length(max=8000)])
    priority = SelectField(
        "Prioridad",
        choices=[
            ("critical", "Crítica"),
            ("high", "Alta"),
            ("medium", "Media"),
            ("low", "Baja"),
        ],
        validators=[DataRequired()],
    )
    effort = SelectField(
        "Esfuerzo",
        choices=[("", "No definido"), ("Bajo", "Bajo"), ("Medio", "Medio"), ("Alto", "Alto")],
        validators=[Optional()],
    )
    suggested_owner = StringField("Responsable sugerido", validators=[Optional(), Length(max=180)])
    time_horizon = SelectField(
        "Horizonte",
        choices=[
            ("", "No definido"),
            ("0-30 días", "0 a 30 días"),
            ("31-90 días", "31 a 90 días"),
            ("3-6 meses", "3 a 6 meses"),
            ("6-12 meses", "6 a 12 meses"),
        ],
        validators=[Optional()],
    )
    due_date = DateField("Fecha objetivo", validators=[Optional()])
    dependencies = TextAreaField("Dependencias", validators=[Optional(), Length(max=8000)])
    status = SelectField(
        "Estado",
        choices=[
            ("open", "Abierta"),
            ("planned", "Planificada"),
            ("in_progress", "En progreso"),
            ("completed", "Completada"),
            ("dismissed", "Descartada"),
        ],
        validators=[DataRequired()],
    )
    is_quick_win = BooleanField("Marcar como quick win")
    target_maturity_level = DecimalField(
        "Nivel objetivo", places=2, validators=[Optional(), NumberRange(min=0, max=3)]
    )
    submit = SubmitField("Guardar recomendación")


class RecommendationStatusForm(FlaskForm):
    status = SelectField(
        "Estado",
        choices=[
            ("open", "Abierta"),
            ("planned", "Planificada"),
            ("in_progress", "En progreso"),
            ("completed", "Completada"),
            ("dismissed", "Descartada"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Actualizar")


class EmptyResultActionForm(FlaskForm):
    submit = SubmitField("Confirmar")
