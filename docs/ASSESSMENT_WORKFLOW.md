# Flujo de assessment

## Estados del assessment

```text
DRAFT
  ├── CONFIGURED
  └── CANCELLED

CONFIGURED
  ├── DRAFT
  ├── IN_PROGRESS
  └── CANCELLED

IN_PROGRESS
  ├── IN_REVIEW
  ├── OBSERVED
  └── CANCELLED

IN_REVIEW
  ├── IN_PROGRESS
  ├── OBSERVED
  ├── COMPLETED
  └── CANCELLED

OBSERVED
  ├── IN_PROGRESS
  ├── IN_REVIEW
  └── CANCELLED

COMPLETED
  ├── IN_REVIEW
  ├── PUBLISHED
  └── CLOSED

PUBLISHED
  ├── IN_REVIEW
  └── CLOSED
```

`CLOSED` y `CANCELLED` son estados terminales.

## Reglas principales

- Solo una versión publicada puede instanciarse.
- Configurado requiere al menos un respondedor y preguntas.
- En ejecución requiere respondedores.
- En revisión requiere al menos una respuesta enviada.
- Completado requiere que todas las preguntas obligatorias estén aprobadas.
- Cerrado o cancelado no puede editarse.

## Estados de respuesta

```text
UNANSWERED → DRAFT → ANSWERED → SUBMITTED
                                  ├── APPROVED
                                  ├── OBSERVED → SUBMITTED
                                  └── REJECTED → SUBMITTED

APPROVED → OBSERVED  (reapertura)
```

La bandera `is_not_applicable` no reemplaza el workflow. Permite que una respuesta No aplica siga el mismo proceso de envío y aprobación, conservando una justificación obligatoria.

## Historial

Cada cambio material incrementa `response_version` y agrega un `ResponseHistory` con:

- Snapshot completo de la respuesta.
- Estado anterior y nuevo.
- Actor.
- Fecha.
- Motivo.

Cada decisión del revisor también crea un registro `Review` asociado a la versión revisada.

## Autorización

### Administrador

- Acceso global.
- Crea y configura assessments.
- Modifica estados.
- Puede revisar cualquier assessment.

### Respondedor

- Ve únicamente assessments con asignación `RESPONDENT`.
- Modifica respuestas solo durante estados habilitados.
- Elimina únicamente evidencia propia y no enviada/aprobada.

### Revisor

- Ve únicamente assessments con asignación `REVIEWER`.
- Revisa respuestas y evidencias.
- Agrega y resuelve observaciones generales.

La aplicación consulta por UUID público y luego valida la asignación. No se autoriza por conocimiento del identificador.
