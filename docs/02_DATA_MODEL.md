# 2. Modelo de datos

## 2.1 Convenciones comunes

Las entidades principales usarán un mixin con:

- `id`: PK interna entera.
- `public_id`: UUID v4 único utilizado en URLs y API.
- `created_at`, `updated_at`: timestamp UTC.
- `created_by_id`, `updated_by_id`: usuario responsable cuando aplique.
- `is_active`: desactivación lógica.
- `deleted_at`: soft delete opcional.
- `row_version`: control de concurrencia optimista.

No se almacenarán secretos, contraseñas en texto claro, tokens ni contenidos completos de evidencia dentro de auditoría.

## 2.2 Identidad y organizaciones

### User

Campos principales:

- `email_normalized` único.
- `display_name`.
- `password_hash` Argon2id.
- `must_change_password`.
- `failed_login_count`.
- `locked_until`.
- `last_login_at`.
- `password_changed_at`.
- `is_active`.

Índices: email normalizado, estado activo y bloqueo.

### Role

- `code`: `admin`, `respondent`, `reviewer`.
- `name`.
- `description`.
- `is_system`.

### UserRole

Relación muchos-a-muchos global entre usuario y rol. Restricción única `(user_id, role_id)`.

### Organization

- `name`, `slug` único.
- `legal_name`, `tax_identifier` opcionales.
- `description`.
- `status`.

### OrganizationMembership

Entidad adicional necesaria para aislamiento multi-organización:

- `organization_id`.
- `user_id`.
- `membership_role`.
- `is_primary`.
- `status`.

Restricción única `(organization_id, user_id)`.

## 2.3 Catálogo SAMM y versionamiento

### BusinessFunction

- `code`, `name`, `description`, `sort_order`.

### SecurityPractice

- `business_function_id`.
- `code`, `name`, `description`, `sort_order`.

Único por `(business_function_id, code)`.

### PracticeStream

- `security_practice_id`.
- `code`, `name`, `description`, `sort_order`.

Único por `(security_practice_id, code)`.

### MaturityLevel

- `level_number`.
- `name`.
- `description`.
- `max_score` por defecto `1.0`.
- `sort_order`.

No se asume que siempre existirán exactamente tres niveles.

### AnswerSet

- `external_code` proveniente del Excel.
- `name`.
- `description`.
- `content_hash`.

### AnswerOption

- `answer_set_id`.
- `option_code`.
- `text`.
- `weight` decimal.
- `sort_order`.

Único por `(answer_set_id, option_code)`.

### Question

Identidad estable de una pregunta:

- `external_code` como `G-SM-A-1-1`.
- `canonical_name` opcional.
- `current_revision_id`.

### QuestionRevision

Versión inmutable del contenido:

- `question_id`.
- `revision_number`.
- `business_function_id`.
- `security_practice_id`.
- `practice_stream_id`.
- `maturity_level_id`.
- `answer_set_id`.
- `question_text`.
- `guidance_text`.
- `content_hash`.
- `supersedes_revision_id`.
- `change_reason`.
- `status`.

Una revisión publicada no se edita; se crea una nueva.

### QuestionQualityCriterion

- `question_revision_id`.
- `criterion_text`.
- `sort_order`.

La columna `Guidance` del Excel se separa por líneas para generar criterios individualizados.

### QuestionnaireVersion

- `name`.
- `version_number`.
- `description`.
- `status`: draft, published, archived.
- `source_name`.
- `source_file_hash`.
- `published_at`, `published_by_id`.

### QuestionnaireVersionQuestion

- `questionnaire_version_id`.
- `question_revision_id`.
- `sort_order`.
- `is_required`.
- `weight_override` opcional.

Único por versión y revisión.

## 2.4 Assessment y ejecución

### Assessment

- `organization_id`.
- `questionnaire_version_id` inmutable tras iniciar.
- `name`, `description`, `scope`.
- `start_date`, `target_date`.
- `status`.
- `target_maturity_level` decimal opcional.
- `scoring_source`: declared, reviewed, approved.
- `results_published_at`, `closed_at`.
- `settings_snapshot` JSON.

### AssessmentUser

- `assessment_id`.
- `user_id`.
- `assignment_role`: respondent o reviewer.
- `is_lead`.
- `assigned_at`.

Único por `(assessment_id, user_id, assignment_role)`.

### AssessmentQuestion

Materialización inmutable de cada pregunta al crear/configurar el assessment:

- `assessment_id`.
- `source_question_revision_id`.
- `external_code_snapshot`.
- `question_text_snapshot`.
- `guidance_snapshot`.
- `criteria_snapshot` JSON.
- `answer_options_snapshot` JSON.
- `business_function_snapshot`.
- `security_practice_snapshot`.
- `practice_stream_snapshot`.
- `maturity_level_snapshot`.
- `sort_order`.
- `is_required`.
- `current_status`.

Esto impide que una edición posterior del catálogo modifique assessments existentes.

### AssessmentResponse

Una fila vigente por `AssessmentQuestion`:

- `assessment_question_id` único.
- `respondent_id`.
- `selected_option_code`.
- `selected_option_text_snapshot`.
- `selected_weight_snapshot`.
- `respondent_comment`.
- `reviewer_comment`.
- `status`.
- `is_not_applicable`.
- `not_applicable_justification`.
- `response_version`.
- `submitted_at`, `reviewed_at`.
- `reviewer_id`.

### ResponseHistory

Registro inmutable por cada cambio relevante:

- `assessment_response_id`.
- `response_version`.
- `snapshot_json`.
- `transition_from`, `transition_to`.
- `changed_by_id`, `changed_at`.
- `reason`.

Único por `(assessment_response_id, response_version)`.

### Evidence

- `assessment_question_id`.
- `assessment_response_id` opcional.
- `response_version`.
- `original_filename`.
- `internal_filename` UUID.
- `storage_key`.
- `reported_mime_type`.
- `detected_mime_type`.
- `extension`.
- `size_bytes`.
- `sha256`.
- `description`.
- `uploaded_by_id`, `uploaded_at`.
- `validation_status`.
- `reviewed_by_id`, `reviewed_at`.
- `deleted_at`.

Índices: assessment question, SHA-256 y estado de validación.

### Review

Evento inmutable de revisión:

- `assessment_response_id`.
- `response_version`.
- `reviewer_id`.
- `decision`: approved, observed, rejected, reopened.
- `comment`.
- `reviewed_at`.

### Recommendation

- `assessment_id`.
- Referencias opcionales a función, práctica, flujo y pregunta materializada.
- `title`, `description`, `risk`.
- `priority`, `effort`, `suggested_owner`.
- `time_horizon`, `dependencies`.
- `status`, `is_quick_win`.
- `target_maturity_level`.

## 2.5 Resultados y trazabilidad

### AssessmentScoreSnapshot

Entidad adicional para reproducibilidad de resultados publicados:

- `assessment_id`.
- `snapshot_number`.
- `scoring_source`.
- `calculated_at`, `calculated_by_id`.
- `overall_score`.
- `progress_percent`.
- `calculation_version`.
- `is_published_snapshot`.

### AssessmentScoreItem

- `score_snapshot_id`.
- `dimension_type`: level, stream, practice, function, overall.
- `dimension_key`, `dimension_name`.
- `score`, `max_score`, `normalized_percent`.
- `target_score`, `gap`.
- `applicable_count`, `not_applicable_count`, `pending_count`.

### AuditLog

- `actor_user_id`.
- `organization_id`, `assessment_id` opcionales.
- `action`.
- `entity_type`, `entity_public_id`.
- `occurred_at`.
- `ip_address`, `user_agent`.
- `before_json`, `after_json` sanitizados.
- `result`, `error_code`.
- `correlation_id`.

La tabla será append-only desde la aplicación.

### ApplicationSetting

- `scope`: global u organization.
- `organization_id` opcional.
- `key`.
- `value_json`.
- `is_secret=false`; los secretos permanecen en entorno/secret manager.

### Notification

- `user_id`.
- `notification_type`.
- `title`, `body`.
- `action_url`.
- `read_at`.

### ImportJob

Entidad adicional para importaciones auditables:

- `source_filename`, `source_sha256`.
- `status`.
- `preview_json`, `errors_json`.
- `created_by_id`, `confirmed_by_id`.
- `started_at`, `completed_at`.
- `created_questionnaire_version_id`.

## 2.6 Restricciones críticas

- Un assessment solo puede apuntar a una versión publicada al comenzar.
- Una versión publicada no puede cambiar sus asociaciones de preguntas.
- Una pregunta materializada pertenece a un solo assessment.
- Una respuesta vigente existe como máximo una vez por pregunta materializada.
- El historial de respuesta y las revisiones son inmutables.
- Una evidencia nunca usa una ruta derivada del nombre entregado por el usuario.
- Toda consulta tenant-scoped debe incluir `organization_id` y autorización.
