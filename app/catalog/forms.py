from __future__ import annotations

from decimal import Decimal

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp, ValidationError

CODE_RE = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"


class ImportUploadForm(FlaskForm):
    workbook = FileField("Archivo SAMM", validators=[FileRequired(), FileAllowed(["xlsx"], "Solo se permiten archivos .xlsx")])
    submit = SubmitField("Validar y previsualizar")


class ImportConfirmForm(FlaskForm):
    version_name = StringField("Nombre de la versión", validators=[DataRequired(), Length(max=180)])
    version_number = StringField("Número de versión", validators=[DataRequired(), Length(max=80), Regexp(CODE_RE, message="Usa letras, números, puntos, guiones o guion bajo.")])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=2000)])
    publish = BooleanField("Publicar inmediatamente")
    submit = SubmitField("Confirmar importación")


class BusinessFunctionForm(FlaskForm):
    code = StringField("Código", validators=[DataRequired(), Length(max=40), Regexp(CODE_RE)])
    name = StringField("Nombre", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=3000)])
    sort_order = IntegerField("Orden", validators=[DataRequired(), NumberRange(min=0, max=9999)], default=0)
    is_active = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar función")


class SecurityPracticeForm(FlaskForm):
    business_function_id = SelectField("Función de negocio", coerce=int, validators=[DataRequired()])
    code = StringField("Código", validators=[DataRequired(), Length(max=40), Regexp(CODE_RE)])
    name = StringField("Nombre", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=3000)])
    sort_order = IntegerField("Orden", validators=[DataRequired(), NumberRange(min=0, max=9999)], default=0)
    is_active = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar práctica")


class PracticeStreamForm(FlaskForm):
    security_practice_id = SelectField("Práctica de seguridad", coerce=int, validators=[DataRequired()])
    code = StringField("Código", validators=[DataRequired(), Length(max=40), Regexp(CODE_RE)])
    name = StringField("Nombre", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=3000)])
    sort_order = IntegerField("Orden", validators=[DataRequired(), NumberRange(min=0, max=9999)], default=0)
    is_active = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar flujo")


class MaturityLevelForm(FlaskForm):
    level_number = IntegerField("Número de nivel", validators=[DataRequired(), NumberRange(min=1, max=99)])
    name = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=3000)])
    max_score = DecimalField("Puntaje máximo", validators=[DataRequired(), NumberRange(min=Decimal("0"), max=Decimal("100"))], places=4, default=Decimal("1"))
    sort_order = IntegerField("Orden", validators=[DataRequired(), NumberRange(min=0, max=9999)], default=0)
    is_active = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar nivel")


class AnswerSetForm(FlaskForm):
    external_code = StringField("Código", validators=[DataRequired(), Length(max=100), Regexp(CODE_RE)])
    name = StringField("Nombre", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=3000)])
    option_a_text = StringField("Alternativa A", validators=[DataRequired(), Length(max=1000)])
    option_a_weight = DecimalField("Ponderación A", validators=[DataRequired(), NumberRange(min=0, max=1)], places=4, default=Decimal("0"))
    option_b_text = StringField("Alternativa B", validators=[DataRequired(), Length(max=1000)])
    option_b_weight = DecimalField("Ponderación B", validators=[DataRequired(), NumberRange(min=0, max=1)], places=4, default=Decimal("0.25"))
    option_c_text = StringField("Alternativa C", validators=[DataRequired(), Length(max=1000)])
    option_c_weight = DecimalField("Ponderación C", validators=[DataRequired(), NumberRange(min=0, max=1)], places=4, default=Decimal("0.5"))
    option_d_text = StringField("Alternativa D", validators=[DataRequired(), Length(max=1000)])
    option_d_weight = DecimalField("Ponderación D", validators=[DataRequired(), NumberRange(min=0, max=1)], places=4, default=Decimal("1"))
    is_active = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar conjunto")

    def validate_option_d_weight(self, field) -> None:
        weights = [self.option_a_weight.data, self.option_b_weight.data, self.option_c_weight.data, field.data]
        if all(value is not None for value in weights) and weights != sorted(weights):
            raise ValidationError("Las ponderaciones deben estar ordenadas de menor a mayor.")

    def options_payload(self) -> list[dict]:
        return [
            {"option_code": "A", "text": self.option_a_text.data, "weight": self.option_a_weight.data},
            {"option_code": "B", "text": self.option_b_text.data, "weight": self.option_b_weight.data},
            {"option_code": "C", "text": self.option_c_text.data, "weight": self.option_c_weight.data},
            {"option_code": "D", "text": self.option_d_text.data, "weight": self.option_d_weight.data},
        ]


class QuestionForm(FlaskForm):
    external_code = StringField("Identificador", validators=[DataRequired(), Length(max=100), Regexp(CODE_RE)])
    canonical_name = StringField("Nombre corto", validators=[Optional(), Length(max=240)])
    business_function_id = SelectField("Función de negocio", coerce=int, validators=[DataRequired()])
    security_practice_id = SelectField("Práctica de seguridad", coerce=int, validators=[DataRequired()])
    practice_stream_id = SelectField("Flujo", coerce=int, validators=[DataRequired()])
    maturity_level_id = SelectField("Nivel de madurez", coerce=int, validators=[DataRequired()])
    answer_set_id = SelectField("Conjunto de respuestas", coerce=int, validators=[DataRequired()])
    question_text = TextAreaField("Pregunta", validators=[DataRequired(), Length(max=10000)])
    guidance_text = TextAreaField("Guía", validators=[Optional(), Length(max=20000)])
    criteria_text = TextAreaField("Criterios de calidad", validators=[Optional(), Length(max=20000)], description="Un criterio por línea.")
    change_reason = StringField("Motivo del cambio", validators=[Optional(), Length(max=500)])
    is_active = BooleanField("Pregunta activa", default=True)
    submit = SubmitField("Guardar revisión")

    def criteria(self) -> list[str]:
        return [line.strip() for line in (self.criteria_text.data or "").splitlines() if line.strip()]


class DuplicateQuestionForm(FlaskForm):
    new_external_code = StringField("Nuevo identificador", validators=[DataRequired(), Length(max=100), Regexp(CODE_RE)])
    submit = SubmitField("Duplicar pregunta")


class QuestionnaireVersionForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=180)])
    version_number = StringField("Número de versión", validators=[DataRequired(), Length(max=80), Regexp(CODE_RE)])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=3000)])
    source_version_id = SelectField("Versión de origen", coerce=int, validators=[Optional()], choices=[])
    submit = SubmitField("Crear versión")


class ConfirmActionForm(FlaskForm):
    submit = SubmitField("Confirmar")
