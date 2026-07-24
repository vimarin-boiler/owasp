# Reporte de validación — Fase 5

Fecha: 24 de julio de 2026.

## Resumen

La entrega fue sometida a validaciones estáticas, estructurales y de migración independientes del runtime Flask.

| Validación | Resultado |
|---|---|
| Compilación Python | Correcta |
| Sintaxis JavaScript | 2 archivos correctos |
| OpenAPI YAML | Correcto |
| Plantillas Jinja2 | 48 correctas |
| Endpoints detectados | 82 |
| Referencias `url_for` | 196, ninguna faltante |
| Iconos usados | 64, ninguno faltante |
| Iconos disponibles | 72 |
| Workbook SAMM | 90 preguntas y estructura esperada |
| Migraciones | Upgrade 0001→0004 y downgrade completo correctos |
| Tablas después del upgrade | 31 |
| Tablas después del downgrade | 0 |
| Pruebas automatizadas incluidas | 54 |
| Placeholders prohibidos | Ninguno |
| Archivos Python | 104 |

## Workbook

La inspección directa de `data/SAMM_spreadsheet.xlsx` confirmó:

- 90 preguntas.
- 24 conjuntos de respuesta.
- 5 funciones.
- 15 prácticas.
- 30 flujos.
- 3 niveles.
- Hojas `imp-questions` e `imp-answers` disponibles.

## Migraciones

Se ejecutaron las funciones de migración directamente con Alembic y SQLite en memoria:

```text
0001_initial
→ 0002_catalog_imports
→ 0003_assessment_workflow
→ 0004_scoring_recommendations
```

El esquema final contiene 31 tablas. Se comprobaron expresamente los campos de snapshots, ítems jerárquicos y recomendaciones agregados en Fase 5. La reversión `0004 → 0001 → vacío` terminó sin tablas residuales.

Las cuatro pruebas de migración también fueron ejecutadas individualmente y finalizaron correctamente.

## Plantillas, rutas e iconos

- Todas las plantillas fueron parseadas con Jinja2.
- Las rutas y nombres de blueprint fueron extraídos mediante AST.
- Las referencias estáticas a `url_for` se contrastaron con 82 endpoints.
- Los identificadores de iconos usados se contrastaron con el sprite local.

## Seguridad

Se verificó la presencia de:

- `default-src 'self'`.
- `frame-ancestors 'none'`.
- Restricción de scripts a origen propio y `cdn.jsdelivr.net`.
- `style-src-attr 'unsafe-inline'` limitado a atributos dinámicos de presentación.
- Autorización diferenciada para ver y administrar resultados.
- Hash SHA-256 en snapshots de cálculo.
- Publicación controlada para respondedores.

## Pruebas automatizadas

La entrega contiene 54 pruebas para autenticación, catálogo, importación, versionamiento, workflow, evidencias, IDOR, scoring, snapshots, publicación, recomendaciones, roadmap, API y migraciones.

La suite completa `pytest` no se ejecutó en el entorno de construcción porque Flask y sus extensiones no estaban instalados, y el entorno no tenía conectividad para descargarlos. No se declara la suite dinámica como aprobada.

Debe ejecutarse en un entorno con dependencias instaladas:

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Herramientas no disponibles

`ruff` no estaba instalado en el entorno de construcción. La validación de sintaxis Python se realizó con `compileall` y AST, pero el lint debe ejecutarse posteriormente:

```bash
ruff check app tests migrations scripts config.py run.py wsgi.py
```

## Conclusión

La estructura, migraciones, plantillas, rutas, recursos y workbook son consistentes. La validación dinámica final debe completarse instalando las dependencias y ejecutando `pytest` antes de promover la solución a un entorno de integración.
