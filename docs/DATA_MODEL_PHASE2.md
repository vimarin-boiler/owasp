# Modelo de datos implementado — Fase 2

La migración inicial crea 29 tablas.

## Identidad

- `users`
- `roles`
- `user_roles`

`UserRole` permite múltiples roles por usuario y registra quién realizó la asignación.

## Organizaciones

- `organizations`
- `organization_memberships`

La membresía está preparada para aislamiento organizacional y asignación futura de usuarios a clientes.

## Catálogo SAMM

- `business_functions`
- `security_practices`
- `practice_streams`
- `maturity_levels`
- `answer_sets`
- `answer_options`
- `questions`
- `question_revisions`
- `question_quality_criteria`
- `questionnaire_versions`
- `questionnaire_version_questions`

Una pregunta tiene identidad estable y revisiones inmutables. Una versión del cuestionario selecciona revisiones concretas.

## Assessment

- `assessments`
- `assessment_users`
- `assessment_questions`

`AssessmentQuestion` conserva snapshots JSON de jerarquía, texto, criterios y alternativas. Las modificaciones posteriores del catálogo no alteran assessments iniciados.

## Respuestas y revisión

- `assessment_responses`
- `response_history`
- `reviews`
- `evidences`

La respuesta actual está separada de su historial. Cada revisión se vincula a una versión específica de la respuesta.

## Resultados y mejora

- `assessment_score_snapshots`
- `assessment_score_items`
- `recommendations`

Los resultados se almacenan como snapshots reproducibles con versión de fórmula.

## Plataforma

- `audit_logs`
- `application_settings`
- `notifications`

## Convenciones

- PK interna entera.
- `public_id` UUID único e indexado.
- `created_at` y `updated_at` en UTC.
- `is_active` y `deleted_at` para maestros con soft delete.
- Claves foráneas con comportamiento explícito `CASCADE`, `RESTRICT` o `SET NULL`.
- Restricciones únicas para evitar duplicados funcionales.
- Enums portables almacenados como cadenas validadas.
