# Reporte de validación — Fase 4

Fecha: 2026-07-24

## Validaciones ejecutadas

| Validación | Resultado |
|---|---|
| Compilación Python | Correcta |
| Configuración de mappers SQLAlchemy | Correcta |
| Creación SQLAlchemy en SQLite en memoria | 31 tablas |
| Migraciones 0001 + 0002 + 0003 | Correctas |
| Downgrade completo | 0 tablas residuales |
| Campo `evidences.review_comment` | Presente |
| Tabla `assessment_review_notes` | Presente |
| Parseo de plantillas Jinja2 | 44 correctas |
| Referencias `url_for` | Sin endpoints faltantes |
| Recursos SVG locales | Sin referencias faltantes |
| Sintaxis JavaScript con Node | Correcta |
| Workbook SAMM de referencia | 90 preguntas, sin errores |

## Pruebas automatizadas incluidas

- Snapshot de preguntas al crear assessments.
- Validación de acceso por asignación.
- Prevención de acceso de usuarios no asignados.
- Guardado, envío, observación, aprobación y reapertura.
- Versionamiento de respuestas.
- Carga, hash, descarga y eliminación de evidencia.
- Rechazo de evidencia duplicada.
- Migración de Fase 4.

## Restricción del entorno de construcción

El entorno utilizado para ensamblar esta entrega no dispone de Flask ni de sus extensiones, y no tiene conectividad para instalar dependencias desde PyPI. Por esa razón no fue posible ejecutar la suite completa `pytest` en este entorno.

La entrega no declara la suite como aprobada sin ejecución. Debe validarse en un entorno con las dependencias instaladas:

```bash
pip install -r requirements-dev.txt
pytest
```

Las validaciones que no dependen del runtime Flask sí fueron ejecutadas y resultaron correctas.
