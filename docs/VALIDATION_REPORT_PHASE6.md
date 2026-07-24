# Reporte de validación - Fase 6

Fecha de validación: 2026-07-24

## Resumen

La Fase 6 fue sometida a validaciones estáticas, estructurales y pruebas aisladas de los componentes que no requieren el runtime Flask completo. No se declara la suite `pytest` como aprobada porque el entorno de construcción no contiene Flask ni sus extensiones y no dispone de conectividad para instalarlas.

## Código y plantillas

- 113 archivos Python analizados.
- Compilación con `compileall` completada sin errores.
- 50 plantillas Jinja2 parseadas correctamente.
- 86 endpoints detectados.
- 208 referencias estáticas a `url_for` contrastadas; ninguna referencia faltante.
- 165 referencias de iconos contrastadas con 72 símbolos SVG locales; ninguna referencia faltante.
- 5 archivos JavaScript validados con `node --check`.
- OpenAPI y Docker Compose cargados correctamente como YAML.
- Scripts de shell validados con `sh -n`.

## Base de datos y migraciones

Se ejecutaron directamente las cuatro migraciones Alembic sobre SQLite mediante `MigrationContext` y `Operations`:

1. `0001_initial.py`
2. `0002_catalog_imports.py`
3. `0003_assessment_workflow.py`
4. `0004_scoring_recommendations.py`

Resultados:

- Upgrade completo: 31 tablas.
- Downgrade completo: 0 tablas residuales.
- La Fase 6 no requiere una nueva migración porque reutiliza las entidades de auditoría, scoring, recomendaciones y evidencias existentes.

## Workbook OWASP SAMM

El archivo `data/SAMM_spreadsheet.xlsx` fue procesado con el parser real:

| Elemento | Resultado |
|---|---:|
| Preguntas | 90 |
| Conjuntos de respuestas | 24 |
| Funciones | 5 |
| Prácticas | 15 |
| Flujos | 30 |
| Niveles | 3 |
| Criterios de calidad | 295 |
| Errores | 0 |
| Advertencias | 0 |

## Reportes

### Excel

Se generó y volvió a abrir un XLSX con `openpyxl`.

- 11 hojas.
- Resumen ejecutivo.
- Funciones, prácticas y flujos.
- Preguntas y evidencias.
- Recomendaciones y roadmap.
- Revisiones, historial y bitácora.
- Tablas, filtros, encabezados inmovilizados y formato condicional.

### PDF

Se generó un PDF de prueba con ReportLab y se verificó mediante las herramientas PDF del entorno.

- 7 páginas A4.
- Documento no cifrado.
- Metadata de título, autor y asunto válida.
- 18 elementos de outline/bookmarks.
- 36 anotaciones internas correspondientes a la tabla de contenidos.
- Renderizado de todas las páginas a PNG a 150 DPI.
- Inspección visual sin texto cortado, superposiciones ni glifos dañados.
- Identidad y clasificación configurables.
- Logotipo PNG/JPEG autorizado opcional mediante `REPORT_LOGO_PATH`.

## Backup y restore

El servicio fue probado de forma aislada con una base SQLite y un directorio de evidencias reales:

- Copia consistente usando `sqlite3.Connection.backup`.
- `PRAGMA integrity_check` exitoso.
- Evidencia incluida en el ZIP.
- Metadata y manifiesto SHA-256 verificados.
- Restauración de la base y las evidencias confirmada.
- Respaldo previo de seguridad confirmado.
- Rechazo de archivo ZIP alterado con miembro no declarado.
- Protección frente a traversal, symlinks, exceso de entradas, tamaño descomprimido y relación de compresión anómala incluida.

## Producción

- Configuración Nginx validada con `nginx -t` usando certificado temporal: exitosa y sin advertencias.
- Unidades `samm-assessment.service`, `samm-assessment-backup.service` y timer verificadas con `systemd-analyze verify` usando rutas ejecutables temporales: sin errores.
- Configuración Gunicorn importada y validada.
- Docker Compose validado sintácticamente como YAML.
- El motor Docker no está disponible en el entorno de construcción, por lo que no se construyó ni ejecutó la imagen.

## Pruebas automatizadas

El proyecto incluye 62 pruebas automatizadas, de las cuales 8 corresponden específicamente a Fase 6:

- Centro de reportes.
- Exportación Excel.
- Exportación PDF.
- Restricción de reportes no publicados.
- Backup con evidencias y hashes.
- Restore con respaldo previo.
- Rechazo de traversal.
- Rechazo de archivos no manifestados.

La ejecución de `python -m pytest` se intentó, pero la colección se detuvo porque el runtime no contiene Flask:

```text
ModuleNotFoundError: No module named 'flask'
```

Después de instalar `requirements-dev.txt`, la validación dinámica debe ejecutarse con:

```bash
python -m pytest
```

## Conclusión

La estructura de la aplicación, migraciones, reportes, workbook, backups y configuraciones operativas son consistentes. Antes de promover a integración o producción se requiere ejecutar la suite completa en el entorno virtual del proyecto y construir la imagen Docker en un host con acceso al registro base y a PyPI.
