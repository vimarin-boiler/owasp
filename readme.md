# NTT DevSecOps Assessment

Plataforma web segura para administrar y ejecutar assessments de madurez DevSecOps basados en OWASP SAMM. La aplicación cubre el ciclo completo: catálogo versionado, organizaciones, assessments, respuestas, evidencias, revisión, scoring, dashboards, recomendaciones, roadmap, reportes y operación productiva.

**Versión de la aplicación:** 0.6.0  
**Runtime:** Python 3.12+  
**Backend:** Flask, SQLAlchemy y Alembic  
**Frontend:** Jinja2, Bootstrap 5, Bootstrap Icons y Chart.js  
**Base inicial:** SQLite, con modelos portables a PostgreSQL

## Capacidades principales

- Autenticación con Argon2, sesiones endurecidas y bloqueo temporal.
- RBAC para administrador, respondedor y revisor.
- Administración de usuarios, roles, organizaciones y assessments.
- Importación del workbook OWASP SAMM mediante `openpyxl`.
- Catálogo jerárquico y versionamiento inmutable de preguntas.
- Snapshot del cuestionario, alternativas y ponderaciones por assessment.
- Cuestionario responsive con borradores, autosave y navegación jerárquica.
- Evidencias privadas con UUID, SHA-256, validación de tipo y protección contra archivos inseguros.
- Flujo de revisión: aprobar, observar, rechazar, corregir y reabrir.
- Motor de madurez 0-3 por pregunta, nivel, flujo, práctica, función y assessment.
- Snapshots reproducibles con hash de entrada y versión de fórmula.
- Dashboards, radar, barras, distribución, matriz de brechas y comparación objetivo.
- Recomendaciones priorizadas y roadmap por horizonte.
- Reportes web imprimibles, Excel y PDF corporativo.
- Backup y restore de SQLite y evidencias con hashes de integridad.
- Docker, Gunicorn, Nginx, systemd, TLS y logrotate documentados.
- API interna versionada bajo `/api/v1/` y OpenAPI.
- Auditoría de las operaciones relevantes.

## Datos SAMM incluidos

`data/SAMM_spreadsheet.xlsx` contiene:

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
Cliente web
   |
   | HTTPS
   v
Nginx
   |
   v
Gunicorn -> Flask Application Factory
             |-- auth / RBAC
             |-- admin / organizaciones
             |-- catalog / importación SAMM
             |-- assessments / respuestas / evidencias
             |-- results / scoring / roadmap
             |-- reports / HTML / XLSX / PDF
             |-- api/v1
             |
             +-- SQLAlchemy -> SQLite / PostgreSQL
             +-- Almacenamiento privado de evidencias
             +-- Auditoría y notificaciones
```

La autorización no depende de UUID públicos. Cada acceso valida rol, asignación al assessment, organización y ownership para prevenir IDOR.

## Estructura del proyecto

```text
samm_assessment/
|-- app/
|   |-- admin/
|   |-- api/v1/
|   |-- assessments/
|   |-- auth/
|   |-- catalog/
|   |-- common/
|   |-- dashboard/
|   |-- models/
|   |-- repositories/
|   |-- reports/
|   |-- results/
|   |-- services/
|   |-- static/
|   `-- templates/
|-- data/SAMM_spreadsheet.xlsx
|-- deploy/
|   |-- logrotate/
|   |-- nginx/
|   |-- scripts/
|   `-- systemd/
|-- docker/
|-- docs/
|-- migrations/versions/
|-- tests/
|-- uploads/
|-- instance/
|-- backups/
|-- reports/
|-- config.py
|-- gunicorn.conf.py
|-- Dockerfile
|-- docker-compose.yml
|-- run.py
`-- wsgi.py
```

El esquema contiene 31 tablas. La Fase 6 no altera el modelo relacional; utiliza auditoría existente para registrar reportes y comandos operativos.

## Requisitos

- Python 3.12 o superior.
- SQLite 3.
- `pip` actualizado.
- Para producción: Linux, Nginx y systemd, o Docker Engine con Compose.

## Instalación local en Linux o macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python scripts/generate_secret.py
```

Edite `.env`, configure un `SECRET_KEY` aleatorio y contraseñas iniciales. Después ejecute:

```bash
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run
```

La aplicación quedará disponible en `http://127.0.0.1:5000`.

## Instalación local en Windows PowerShell

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

## Configuración mínima

```env
FLASK_ENV=development
SECRET_KEY=replace-with-at-least-32-random-bytes
DATABASE_URL=sqlite:///instance/samm_assessment.db

INITIAL_ADMIN_NAME=Administrador
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=Change-Me-Now-2026!

UPLOAD_FOLDER=uploads
BACKUP_FOLDER=backups
REPORT_FOLDER=reports
MAX_CONTENT_LENGTH_MB=20
MAX_EVIDENCE_FILES_PER_QUESTION=10
ALLOWED_EXTENSIONS=pdf,docx,xlsx,pptx,txt,csv,png,jpg,jpeg,zip

SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
ASSESSMENT_AUTOSAVE_SECONDS=30
APP_NAME=NTT DevSecOps Assessment
```

En producción:

```env
FLASK_ENV=production
SESSION_COOKIE_SECURE=true
FORCE_HTTPS=true
TRUSTED_HOSTS=assessment.example.com
CREATE_DEMO_DATA=false
```

## Inicialización

`flask seed` es idempotente y realiza:

1. Creación de los roles `admin`, `respondent` y `reviewer`.
2. Creación del administrador inicial.
3. Importación y publicación del workbook configurado, si no existe una versión.
4. Creación opcional de usuarios y assessment demo cuando `CREATE_DEMO_DATA=true`.

Las credenciales provienen de variables de entorno y obligan a cambiar la contraseña en el primer acceso.

## Importación SAMM

Validación sin persistir cambios:

```bash
flask --app run.py import-samm --file data/SAMM_spreadsheet.xlsx --dry-run
```

Importación como borrador:

```bash
flask --app run.py import-samm \
  --file data/SAMM_spreadsheet.xlsx \
  --version 2.2.0 \
  --name "OWASP SAMM 2.2.0"
```

Importación y publicación:

```bash
flask --app run.py import-samm \
  --file data/SAMM_spreadsheet.xlsx \
  --version 2.2.0 \
  --publish
```

## Flujo funcional

1. Publicar una versión del cuestionario.
2. Crear organización y assessment.
3. Definir alcance, fechas, nivel objetivo y fuente de scoring.
4. Asignar respondedores y revisores.
5. Iniciar el assessment.
6. Responder y adjuntar evidencias.
7. Enviar preguntas a revisión.
8. Aprobar, observar o rechazar.
9. Corregir y reenviar cuando corresponda.
10. Completar y publicar resultados.
11. Crear recomendaciones y roadmap.
12. Generar entregables HTML, Excel o PDF.

Los respondedores solo ven resultados y reportes cuando existe un snapshot publicado. Administradores y revisores asignados pueden previsualizar el cálculo vigente.

## Metodología de scoring

- Escala general de 0 a 3.
- Fuente declarada: respuestas respondidas o posteriores.
- Fuente revisada: respuestas con revisión registrada.
- Fuente aprobada: solo respuestas aprobadas.
- “No aplica” elegible se excluye del denominador.
- Preguntas aplicables pendientes permanecen con valor cero.
- Los niveles se calculan desde preguntas; los flujos se normalizan a 0-3.
- Prácticas, funciones y resultado general usan promedios de dimensiones aplicables.

Consulte `docs/SCORING_METHODOLOGY.md`.

## Reportes

Desde la vista de resultados se accede al centro de reportes:

- **Vista web imprimible:** resumen, funciones, prácticas, brechas, recomendaciones, roadmap, evidencias y trazabilidad.
- **Excel:** hojas de resumen, funciones, prácticas, flujos, preguntas, evidencias, recomendaciones, roadmap, revisiones, historial y bitácora.
- **PDF:** portada, tabla de contenidos, gráficos vectoriales, resultados, matriz de brechas, recomendaciones, roadmap y anexos.

Los archivos se generan en memoria y se descargan con `Cache-Control: no-store`. Cada generación queda registrada en auditoría. No se incorporan evidencias binarias al PDF; se incluyen sus metadatos y hashes.

## Backup y restore

Crear respaldo:

```bash
flask --app run.py backup
```

Indicar nombre o ruta:

```bash
flask --app run.py backup --output backups/manual.zip
```

Validar y restaurar:

```bash
flask --app run.py restore --file backups/manual.zip
```

Restauración no interactiva:

```bash
flask --app run.py restore --file backups/manual.zip --yes
```

El respaldo contiene:

- Copia consistente de SQLite mediante la API de backup.
- Evidencias privadas, excluyendo cuarentena.
- `metadata.json`.
- `manifest.json` con SHA-256 y tamaño de cada archivo.

La restauración valida rutas, enlaces simbólicos, tamaño, relación de compresión, hashes y `PRAGMA integrity_check`. De forma predeterminada crea un respaldo de seguridad previo. Detalles en `docs/BACKUP_RESTORE.md`.

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Análisis estático:

```bash
ruff check .
python -m compileall app tests
```

## Docker

```bash
cp .env.example .env
# Configure secretos y valores de producción.
docker compose build
docker compose up -d
```

Abra `http://localhost:8080`.

El contenedor:

- Se ejecuta con usuario no root UID 10001.
- Aplica migraciones al iniciar.
- Mantiene volúmenes separados para base, evidencias, reportes y backups.
- Usa `no-new-privileges` y elimina capacidades innecesarias.
- Expone healthcheck en `/api/v1/health`.

Consulte `docs/DOCKER.md`.

## Producción Linux

La entrega incluye:

- `gunicorn.conf.py`.
- `deploy/nginx/samm-assessment.conf`.
- `deploy/systemd/samm-assessment.service`.
- Timer diario de backup.
- Configuración logrotate.
- Script de instalación base.

Guía completa: `docs/DEPLOYMENT_LINUX.md`.

## API interna

- Documento OpenAPI: `/api/v1/openapi.yaml`.
- Healthcheck: `/api/v1/health`.
- Catálogo, assessments, respuestas, evidencias, resultados y recomendaciones.
- Enlaces autorizados de reportes: `/api/v1/reports/{assessment_id}/`.

La API usa la sesión autenticada y las mismas reglas de autorización que la interfaz.

## Seguridad

- Argon2 para contraseñas.
- CSRF en formularios.
- ORM y consultas parametrizadas.
- Escape Jinja2.
- Cookies `HttpOnly`, `SameSite` y `Secure` en producción.
- Expiración absoluta e inactividad de sesión.
- Rate limiting.
- CSP, HSTS, protección clickjacking y MIME sniffing.
- UUID públicos más autorización contextual.
- Evidencias fuera de `static` y descarga autenticada.
- Hashes SHA-256 y auditoría.
- Secretos solo mediante variables de entorno.
- Errores sin stack trace en producción.

Revise `docs/PRODUCTION_SECURITY_CHECKLIST.md` antes de publicar el servicio.

## Evolución a PostgreSQL

Los modelos y servicios no dependen de SQL específico de SQLite. Para migrar:

1. Instale el driver PostgreSQL, por ejemplo `psycopg[binary]`.
2. Configure `DATABASE_URL=postgresql+psycopg://...`.
3. Ejecute `flask db upgrade` sobre una base vacía.
4. Migre los datos mediante una herramienta controlada.
5. Reemplace los comandos integrados de backup/restore por mecanismos nativos de PostgreSQL.

La lógica funcional y los repositorios no requieren cambios.

## Credenciales de demostración

Solo se crean cuando `CREATE_DEMO_DATA=true`. Los correos y contraseñas se toman de `.env`. Todas las cuentas iniciales exigen cambio de contraseña.

## Limitaciones conocidas

- SQLite está orientado a una única instancia de aplicación y carga moderada.
- El adaptador antivirus por defecto no analiza malware; debe integrarse ClamAV o un servicio equivalente.
- Los reportes PDF usan tipografías estándar. Puede incorporarse un logotipo PNG/JPEG autorizado mediante `REPORT_LOGO_PATH`; el proyecto no distribuye logotipos protegidos.
- La generación de reportes se ejecuta en el proceso web. Para grandes volúmenes conviene migrarla a una cola asíncrona.
- Los backups integrados son exclusivos de SQLite.
- Chart.js se obtiene desde una URL configurable; puede servirse localmente en entornos aislados.

## Documentación

- `docs/PHASE_6_DELIVERY.md`
- `docs/REPORTING.md`
- `docs/BACKUP_RESTORE.md`
- `docs/DOCKER.md`
- `docs/DEPLOYMENT_LINUX.md`
- `docs/PRODUCTION_SECURITY_CHECKLIST.md`
- `docs/SCORING_METHODOLOGY.md`
- `docs/openapi-v1.yaml`
