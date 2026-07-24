# Hotfix 0.6.5: creación de assessments y autoflush

## Síntoma

Al crear un assessment, SQLAlchemy terminaba con `AssertionError` dentro de `Session._autoflush()` mientras se generaban las preguntas snapshot.

## Causa

La implementación anterior combinaba dos condiciones:

1. `QuestionRevision.question` se resolvía mediante lazy loading durante el snapshot.
2. El nuevo `AssessmentQuestion` se construía con `assessment=assessment` y luego se volvía a agregar mediante `assessment.questions.append(...)`.

La consulta lazy disparaba autoflush mientras la colección mantenía mutaciones pendientes y la misma instancia estaba siendo asociada dos veces.

## Corrección

- `QuestionRevision.question` se precarga mediante `selectinload`.
- `_snapshot_question()` devuelve una instancia aún no asociada.
- `_replace_questions()` construye primero toda la lista dentro de `db.session.no_autoflush` y luego reemplaza la colección una sola vez.

No requiere una nueva migración de base de datos.
