# NTT DevSecOps Assessment — Fase 3

Plataforma web segura para administrar assessments de madurez DevSecOps basados en OWASP SAMM.

Esta entrega incorpora la **Fase 3: Catálogo SAMM** sobre la base ejecutable de la Fase 2. Incluye importación transaccional desde Excel, administración de la jerarquía, preguntas con revisiones inmutables, conjuntos de respuesta ponderados, versiones publicables y exportación compatible.

## Capacidades disponibles

### Base de aplicación

- Python 3.12 o superior y Flask con Application Factory.
- SQLAlchemy 2.x, Flask-Migrate y Alembic.
- SQLite para desarrollo, con modelos portables a PostgreSQL.
- Autenticación Flask-Login y contraseñas Argon2.
- RBAC para administrador, respondedor y revisor.
- Protección CSRF, rate limiting, CSP y encabezados de seguridad.
- Auditoría con actor, IP, User-Agent, valores anteriores y posteriores.
- Bootstrap 5 e iconos locales con estilo corporativo NTT.

### Catálogo SAMM

- Importación de `SAMM_spreadsheet.xlsx` mediante `openpyxl`.
- Vista previa antes de confirmar.
- Validación por hoja, fila y campo.
- Verificación segura del contenedor XLSX.
- Hash SHA-256 del archivo fuente.
- Prevención de duplicados mediante hashes de contenido.
- Rollback completo ante errores.
- CRUD de funciones, prácticas, flujos y niveles.
- Administración de conjuntos de respuestas y ponderaciones.
- Preguntas con criterios de calidad e historial de revisiones.
- Duplicación de preguntas.
- Versiones de cuestionario en borrador, publicadas o archivadas.
- Exportación a Excel de cualquier versión.
- API autenticada de preguntas y versiones.

## Resultado del archivo incluido

El archivo `data/SAMM_spreadsheet.xlsx` fue validado con el siguiente resultado:

| Elemento | Cantidad |
|---|---:|
| Funciones de negocio | 5 |
| Prácticas de seguridad | 15 |
| Flujos | 30 |
| Niveles de madurez | 3 |
| Preguntas | 90 |
| Conjuntos de respuesta | 24 |
| Criterios de calidad | 295 |

No se detectaron errores ni advertencias.

## Estructura principal

```text
samm_assessment/
├── app/
│   ├── admin/                    # Usuarios, roles, organizaciones y auditoría
│   ├── api/v1/                   # API versionada
│   ├── auth/                     # Login y cambio de contraseña
│   ├── catalog/                  # Interfaz del catálogo SAMM
│   ├── common/                   # Seguridad, errores y validadores
│   ├── dashboard/                # Dashboard por rol
│   ├── models/                   # 30 tablas SQLAlchemy
│   ├── repositories/             # Consultas y carga de relaciones
│   ├── services/                 # Importación, catálogo y versionamiento
│   ├── static/                   # CSS, JS, Bootstrap e iconos
│   └── templates/                # Layout y componentes Jinja2
├── data/
│   └── SAMM_spreadsheet.xlsx     # Fuente inicial del catálogo
├── docs/
├── migrations/
│   └── versions/
│       ├── 0001_initial.py
│       └── 0002_catalog_imports.py
├── tests/
├── uploads/
├── instance/
├── config.py
├── run.py
├── requirements.txt
└── requirements-dev.txt
```

## Requisitos

- Python 3.12 o superior.
- SQLite 3.
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

Configura en `.env` una clave segura y una contraseña inicial:

```env
SECRET_KEY=<valor-aleatorio-de-al-menos-32-caracteres>
INITIAL_ADMIN_PASSWORD=<contraseña-temporal-segura>
SAMM_IMPORT_FILE=data/SAMM_spreadsheet.xlsx
SAMM_DEFAULT_VERSION=2.2.0
```

Inicializa la plataforma:

```bash
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run
```

`flask seed` crea los roles, el administrador, la organización de demostración y, si aún no existe una versión, importa y publica el Excel configurado en `SAMM_IMPORT_FILE`.

La aplicación quedará disponible en:

```text
http://127.0.0.1:5000
```

## Instalación en Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python .\scripts\generate_secret.py
```

Después de configurar `.env`:

```powershell
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run
```

## Importación desde Excel

### Desde la interfaz

1. Ingresa con rol administrador.
2. Abre **Catálogo SAMM**.
3. Selecciona **Importar Excel**.
4. Carga el archivo `.xlsx`.
5. Revisa el resumen y los errores por fila.
6. Define el nombre y número de versión.
7. Confirma como borrador o publica inmediatamente.

### Desde CLI

Solo validar:

```bash
flask --app run.py import-samm \
  --file data/SAMM_spreadsheet.xlsx \
  --dry-run
```

Importar como borrador:

```bash
flask --app run.py import-samm \
  --file data/SAMM_spreadsheet.xlsx \
  --name "OWASP SAMM 2.2.0" \
  --version 2.2.0
```

Importar y publicar:

```bash
flask --app run.py import-samm \
  --file data/SAMM_spreadsheet.xlsx \
  --name "OWASP SAMM 2.2.0" \
  --version 2.2.0 \
  --publish
```

## Versionamiento

- Cada pregunta tiene un identificador estable y una o más revisiones.
- Editar una pregunta crea la siguiente revisión.
- Las revisiones anteriores nunca se sobrescriben.
- Una versión enlaza revisiones concretas y ordenadas.
- Publicar una versión archiva la versión publicada anterior.
- Los conjuntos de respuesta ya utilizados no pueden modificarse.
- Los elementos jerárquicos utilizados no permiten alterar código, nombre ni relación padre.

## Exportación

Desde el detalle de una versión usa **Exportar**. Se genera un workbook con:

- `Metadata`
- `imp-questions`
- `imp-answers`

El resultado puede volver a validarse con el importador.

## Migraciones

Aplicar todas las migraciones:

```bash
flask --app run.py db upgrade
```

Revertir la última migración:

```bash
flask --app run.py db downgrade
```

La Fase 3 agrega la tabla `catalog_imports`, llevando el esquema a 30 tablas.

## API v1

### Healthcheck público

```http
GET /api/v1/health
```

### Catálogo autenticado

```http
GET /api/v1/questions/
GET /api/v1/questions/{uuid}/
GET /api/v1/questionnaire-versions/
```

Las rutas del catálogo requieren un usuario autenticado con rol administrador, revisor o respondedor.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

Con cobertura:

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```

La suite incluye pruebas de:

- Parser del Excel real.
- Validación de hojas obligatorias.
- Importación completa.
- Reimportación idempotente.
- Rollback.
- Revisiones de preguntas.
- Exportación Excel.
- Autorización de rutas.
- Migraciones.

## Seguridad específica del importador

- Solo acepta `.xlsx`.
- Usa `secure_filename` para el nombre presentado.
- Genera un nombre interno aleatorio.
- Almacena cargas temporales fuera de `static`.
- Limita el tamaño del archivo.
- Valida cantidad y tamaño descomprimido de los elementos internos.
- Rechaza relaciones de compresión anómalas.
- Calcula SHA-256.
- No ejecuta macros ni fórmulas.
- Procesa el libro en modo lectura y `data_only`.
- Ejecuta la aplicación del catálogo dentro de una única transacción.
- Elimina el archivo temporal después de confirmar.

## Configuración relevante

```env
CATALOG_IMPORT_FOLDER=instance/catalog_imports
MAX_CATALOG_IMPORT_MB=15
SAMM_IMPORT_FILE=data/SAMM_spreadsheet.xlsx
SAMM_DEFAULT_VERSION=2.2.0
```

## Documentación

- `docs/PHASE_3_DELIVERY.md`
- `docs/IMPORT_FORMAT.md`
- `docs/CATALOG_VERSIONING.md`
- `docs/VALIDATION_REPORT_PHASE3.md`
- Documentación de las fases 1 y 2 conservada en `docs/`.

## Alcance pendiente

La Fase 4 incorporará:

- Creación de assessments.
- Asignación de respondedores y revisores.
- Instanciación de preguntas desde una versión.
- Respuestas, borradores y transiciones de estado.
- Evidencias privadas y flujo de revisión.

Las fases 5 y 6 incorporarán scoring, dashboards, brechas, recomendaciones, roadmap, reportes y despliegue productivo completo.
