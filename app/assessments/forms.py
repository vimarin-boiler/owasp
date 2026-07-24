from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    HiddenField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class AssessmentForm(FlaskForm):
    organization_id = SelectField("Organización", coerce=int, validators=[DataRequired()])
    questionnaire_version_id = SelectField("Versión del cuestionario", coerce=int, validators=[DataRequired()])
    name = StringField("Nombre", validators=[DataRequired(), Length(max=220)])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=5000)])
    scope = TextAreaField("Alcance", validators=[Optional(), Length(max=5000)])
    start_date = DateField("Fecha de inicio", validators=[Optional()])
    target_date = DateField("Fecha objetivo", validators=[Optional()])
    target_maturity_level = DecimalField(
        "Nivel objetivo", validators=[Optional(), NumberRange(min=0, max=3)], places=2
    )
    scoring_source = SelectField(
        "Fuente para el cálculo",
        choices=[
            ("declared", "Respuesta declarada"),
            ("reviewed", "Respuesta revisada"),
            ("approved", "Respuesta aprobada final"),
        ],
        validators=[DataRequired()],
    )
    respondent_ids = SelectMultipleField("Respondedores", coerce=int, validators=[Optional()])
    reviewer_ids = SelectMultipleField("Revisores", coerce=int, validators=[Optional()])
    submit = SubmitField("Guardar assessment")


class ResponseForm(FlaskForm):
    selected_option_code = RadioField("Respuesta", validators=[Optional()])
    respondent_comment = TextAreaField(
        "Comentario o justificación", validators=[Optional(), Length(max=10000)]
    )
    is_not_applicable = BooleanField("Esta pregunta no aplica")
    not_applicable_justification = TextAreaField(
        "Justificación de no aplicabilidad", validators=[Optional(), Length(max=5000)]
    )
    save_draft = SubmitField("Guardar borrador")
    save = SubmitField("Guardar respuesta")
    submit_review = SubmitField("Enviar a revisión")


class EvidenceUploadForm(FlaskForm):
    evidences = MultipleFileField("Archivos", validators=[DataRequired()])
    description = StringField("Descripción", validators=[Optional(), Length(max=500)])
    upload = SubmitField("Adjuntar evidencias")


class ReviewForm(FlaskForm):
    decision = RadioField(
        "Decisión",
        choices=[
            ("approved", "Aprobar"),
            ("observed", "Observar"),
            ("rejected", "Rechazar"),
        ],
        validators=[DataRequired()],
    )
    comment = TextAreaField("Observación del revisor", validators=[Optional(), Length(max=10000)])
    submit = SubmitField("Registrar revisión")


class ReopenForm(FlaskForm):
    comment = TextAreaField("Motivo de reapertura", validators=[DataRequired(), Length(max=5000)])
    submit = SubmitField("Reabrir pregunta")


class EvidenceReviewForm(FlaskForm):
    evidence_public_id = HiddenField(validators=[DataRequired()])
    validation_status = SelectField(
        "Estado",
        choices=[("valid", "Válida"), ("rejected", "Rechazada")],
        validators=[DataRequired()],
    )
    comment = StringField("Comentario", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Validar evidencia")


class ReviewNoteForm(FlaskForm):
    body = TextAreaField("Observación general", validators=[DataRequired(), Length(max=10000)])
    submit = SubmitField("Agregar observación")


class EmptyActionForm(FlaskForm):
    submit = SubmitField("Confirmar")
