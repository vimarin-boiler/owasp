# NTT DevSecOps Assessment — Fase 4

Aplicación web segura para administrar y ejecutar assessments de madurez DevSecOps basados en OWASP SAMM.

Esta entrega incorpora la **Fase 4: ejecución del assessment** sobre el catálogo versionado de la Fase 3. Permite crear assessments por organización, instanciar snapshots inmutables del cuestionario, asignar respondedores y revisores, responder preguntas, adjuntar evidencias privadas y completar el ciclo de revisión.

## Estado de la solución

### Disponible en esta fase

- Application Factory Flask y Blueprints modulares.
- SQLAlchemy 2.x, Flask-Migrate y Alembic.
- SQLite con diseño portable a PostgreSQL.
- Autenticación, Argon2, cambio obligatorio de contraseña y bloqueo temporal.
- RBAC para administrador, respondedor y revisor.
- Administración de usuarios, roles y organizaciones.
- Catálogo OWASP SAMM importable y versionado.
- Creación y edición de assessments.
- Asignación de respondedores y revisores.
- Snapshot histórico de preguntas, jerarquía, criterios, alternativas y ponderaciones.
- Cuestionario navegable con filtros, búsqueda y progreso.
- Guardado como borrador, respuesta y autosave.
- Envío a revisión, aprobación, observación, rechazo y reapertura.
- Observaciones generales del assessment.
- Evidencias múltiples por pregunta con almacenamiento privado.
- Auditoría y notificaciones internas.
- API REST interna `/api/v1/` y especificación OpenAPI.
- Bootstrap 5, Bootstrap Icons y Chart.js locales.

### Próximas fases

- Fase 5: motor de puntuación, dashboards de resultados, brechas, recomendaciones y roadmap.
- Fase 6: reportes PDF/Excel finales, backup/restore, Docker y despliegue productivo documentado.

## Datos SAMM incluidos

El workbook `data/SAMM_spreadsheet.xlsx` contiene y valida:

| Elemento | Cantidad |
|---|---:|
| Funciones de negocio | 5 |
| Prácticas de seguridad | 15 |
| Flujos | 30 |
| Niveles de madurez | 3 |
| Preguntas | 90 |
| Conjuntos de respuesta | 24 |
| Criterios de calidad | 295 |

## Arquitectura

```text
Navegador
   │ HTTPS / sesión / CSRF
   ▼
Nginx (fase de despliegue)
   │
   ▼
Gunicorn → Flask Application Factory
             ├── auth
             ├── admin
             ├── catalog
             ├── assessments
             ├── dashboard
             └── api/v1
                    │
      ┌─────────────┴─────────────┐
      ▼                           ▼
SQLAlchemy/Alembic         EvidenceService
SQLite o PostgreSQL        almacenamiento privado
```

La lógica funcional se divide en controladores, formularios, servicios y repositorios. Las rutas nunca consultan un assessment únicamente por UUID: también aplican validaciones de rol, asignación y ownership.

## Estructura principal

```text
samm_assessment/
├── app/
│   ├── admin/
│   ├── api/v1/
│   ├── assessments/
│   ├── auth/
│   ├── catalog/
│   ├── common/
│   ├── dashboard/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   ├── static/
│   └── templates/
├── data/SAMM_spreadsheet.xlsx
├── docs/
├── migrations/versions/
│   ├── 0001_initial.py
│   ├── 0002_catalog_imports.py
│   └── 0003_assessment_workflow.py
├── tests/
├── uploads/
├── instance/
├── config.py
├── run.py
├── requirements.txt
└── requirements-dev.txt
```

El esquema de la Fase 4 contiene **31 tablas**.

## Requisitos

- Python 3.12 o superior.
- SQLite 3 para desarrollo.
- Windows, Linux o macOS.

## Instalación en Linux o macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python scripts/generate_secret.py
```

Copia el valor generado a `SECRET_KEY` y reemplaza todas las contraseñas de ejemplo. Luego ejecuta:

```bash
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run
```

La aplicación quedará disponible en `http://127.0.0.1:5000`.

## Instalación en Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python .\scripts\generate_secret.py
```

Después de editar `.env`:

```powershell
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run
```

## Inicialización y usuarios demo

`flask seed` realiza de forma idempotente:

1. Creación de roles.
2. Creación del administrador inicial.
3. Creación de la organización demo.
4. Importación y publicación del workbook configurado.
5. Creación opcional de respondedor y revisor demo.
6. Creación opcional de un assessment SAMM iniciado.

La creación de datos demo está **deshabilitada por defecto en el código**. El archivo `.env.example` la habilita explícitamente con:

```env
CREATE_DEMO_DATA=true
```

Para producción usa `CREATE_DEMO_DATA=false`.

Todos los usuarios iniciales quedan obligados a cambiar su contraseña en el primer acceso.

## Flujo administrativo

1. Publicar una versión del cuestionario SAMM.
2. Crear o seleccionar una organización.
3. Crear un assessment.
4. Elegir la versión publicada y el nivel objetivo.
5. Asignar uno o más respondedores y revisores.
6. Cambiar el estado a **En ejecución**.
7. Supervisar avance y revisiones.
8. Completar el assessment cuando todas las preguntas requeridas estén aprobadas.

Al crear el assessment, la aplicación copia el contenido de cada pregunta a `assessment_questions`. Las modificaciones futuras del catálogo no alteran evaluaciones ya iniciadas.

## Flujo del respondedor

- Visualiza únicamente assessments asignados.
- Filtra por función, práctica, flujo y estado.
- Busca preguntas por código o texto.
- Guarda borradores manualmente o mediante autosave.
- Selecciona una alternativa o marca **No aplica** con justificación.
- Adjunta múltiples evidencias.
- Envía la respuesta a revisión.
- Corrige respuestas observadas o rechazadas.

El estado de workflow y la aplicabilidad son dimensiones independientes: una respuesta marcada como no aplicable puede estar en borrador, enviada o aprobada, conservando siempre su justificación.

## Flujo del revisor

- Accede solo a assessments asignados, salvo el administrador global.
- Consulta una cola de respuestas enviadas.
- Revisa respuesta, comentarios y evidencias.
- Valida o rechaza cada evidencia.
- Aprueba, observa o rechaza la respuesta.
- Reabre respuestas previamente aprobadas.
- Registra observaciones generales y las marca como resueltas.

Cada transición genera historial de respuesta, registro de revisión, auditoría y notificaciones internas.

## Evidencias

Extensiones iniciales:

```text
pdf, docx, xlsx, pptx, txt, csv, png, jpg, jpeg, zip
```

Controles implementados:

- 20 MB por archivo, configurable.
- Cantidad máxima por pregunta configurable.
- Almacenamiento fuera de `static`.
- Directorios por UUID de assessment y pregunta.
- Nombre interno aleatorio UUID.
- `secure_filename` para el nombre presentado.
- Comprobación de firma y tipo efectivo.
- Inspección del contenido ZIP/Office.
- Rechazo de traversal, symlinks, ejecutables, scripts y bombas ZIP.
- Cuarentena temporal antes de mover el archivo.
- Hash SHA-256 y prevención de duplicados.
- Interfaz preparada para antivirus o ClamAV.
- Autorización antes de descargar o eliminar.
- Descarga forzada con `nosniff`, `sandbox` y `no-store`.

El scanner incluido es un adaptador nulo seguro para desarrollo. En producción debe reemplazarse por una implementación antivirus real antes de aceptar archivos externos.

## Configuración relevante

```env
DATABASE_URL=sqlite:///instance/samm_assessment.db
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH_MB=20
MAX_EVIDENCE_FILES_PER_QUESTION=10
MAX_REQUEST_CONTENT_LENGTH_MB=200
ALLOWED_EXTENSIONS=pdf,docx,xlsx,pptx,txt,csv,png,jpg,jpeg,zip
ASSESSMENT_AUTOSAVE_SECONDS=30
SAMM_IMPORT_FILE=data/SAMM_spreadsheet.xlsx
SAMM_DEFAULT_VERSION=2.2.0
```

`MAX_CONTENT_LENGTH_MB` controla cada archivo. `MAX_REQUEST_CONTENT_LENGTH_MB` limita el request HTTP completo.

## Importación SAMM

Validar sin persistir:

```bash
flask --app run.py import-samm --file data/SAMM_spreadsheet.xlsx --dry-run
```

Importar y publicar:

```bash
flask --app run.py import-samm \
  --file data/SAMM_spreadsheet.xlsx \
  --name "OWASP SAMM 2.2.0" \
  --version 2.2.0 \
  --publish
```

## Migraciones

```bash
flask --app run.py db upgrade
flask --app run.py db current
flask --app run.py db downgrade
```

La migración `0003_assessment_workflow` agrega las observaciones generales y comentarios de revisión de evidencia.

## API v1

- `GET /api/v1/health`
- `GET /api/v1/openapi.yaml`
- `GET /api/v1/questions/`
- `GET /api/v1/questionnaire-versions/`
- `GET /api/v1/assessments/`
- `GET /api/v1/assessments/{uuid}/`
- `GET /api/v1/assessments/{uuid}/questions/`
- `PUT /api/v1/responses/{assessment_question_uuid}/`
- `GET /api/v1/evidences/{uuid}/`

La API usa la sesión autenticada de la aplicación. Los endpoints de escritura siguen protegidos por CSRF cuando se consumen desde el navegador.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

Con cobertura:

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```

La suite incluye escenarios de:

- Creación y snapshot de assessments.
- Aislamiento por asignación e IDOR.
- Guardado, envío, revisión y reapertura.
- Evidencias, hash, duplicados y eliminación.
- Autenticación y autorización.
- Importación y versionamiento SAMM.
- Migraciones.

También existe un smoke test:

```bash
python scripts/smoke_check.py
```

## Seguridad operativa

Antes de producción:

- Usa `FLASK_ENV=production`.
- Configura `SESSION_COOKIE_SECURE=true` y TLS.
- Usa una `SECRET_KEY` aleatoria y rotada de forma controlada.
- Configura `TRUSTED_HOSTS` con nombres reales.
- Reemplaza el almacenamiento local si se necesita alta disponibilidad.
- Integra ClamAV o un servicio antimalware.
- Configura un backend compartido para rate limiting.
- Restringe permisos del directorio `uploads` al usuario del servicio.
- Migra a PostgreSQL para concurrencia y operación multiinstancia.

## Documentación adicional

- `docs/PHASE_4_DELIVERY.md`
- `docs/ASSESSMENT_WORKFLOW.md`
- `docs/EVIDENCE_SECURITY.md`
- `docs/openapi-v1.yaml`
- `docs/VALIDATION_REPORT_PHASE4.md`
- `docs/PROJECT_TREE_PHASE4.txt`

## Limitaciones conocidas de esta fase

- El cálculo consolidado de madurez y brechas se implementará en la Fase 5.
- La publicación actual solo registra el estado; la visualización de resultados se habilitará con el motor de scoring.
- El antivirus por defecto no analiza malware; solo implementa el contrato de integración.
- Los respaldos, reportes PDF finales y artefactos de despliegue pertenecen a la Fase 6.
