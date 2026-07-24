# Entrega Fase 5 — Resultados, brechas y roadmap

## 1. Objetivo

La Fase 5 transforma las respuestas del assessment en información de gestión reproducible. Incorpora el motor de madurez, snapshots de resultados, dashboards, análisis de brechas, recomendaciones priorizadas y roadmap.

## 2. Alcance implementado

### Motor de puntuación

- Escala comparable de 0 a 3.
- Fuentes declarada, revisada y aprobada.
- Cálculo por pregunta, nivel, flujo, práctica, función y assessment.
- Exclusión de preguntas no aplicables elegibles.
- Preguntas pendientes aplicables con valor cero.
- Nivel actual, nivel objetivo y brecha.
- Progreso y resumen de estados.
- Conteo de evidencias cargadas, pendientes, validadas y rechazadas.

### Persistencia de resultados

- Snapshot secuencial por assessment.
- Hash SHA-256 de la entrada.
- Versión de la fórmula.
- Fuente de scoring.
- Usuario y fecha de cálculo.
- Resumen de estados y metadatos.
- Detalle jerárquico persistido.
- Publicación exclusiva de un snapshot vigente.

### Dashboards

- Dashboard administrativo con KPIs globales.
- Dashboard de respondedor con estado de sus asignaciones.
- Radar por función.
- Barras por práctica.
- Distribución de estados.
- Comparación actual versus objetivo.
- Distribución de avance.
- Lista de brechas principales.

### Recomendaciones

- Creación, edición, cambio de estado y desactivación lógica.
- Asociación a función, práctica, flujo o pregunta.
- Prioridad, esfuerzo, riesgo, responsable, horizonte, dependencias y quick win.
- Generación determinística desde brechas de práctica.
- Prevención de duplicados activos por dimensión.

### Roadmap

- Agrupación por 0–30 días, 31–90 días, 3–6 meses, 6–12 meses y sin horizonte.
- Indicadores de total, quick wins, completadas y críticas.
- Visibilidad condicionada por permisos y publicación.

### API

- `GET /api/v1/results/{assessment_uuid}/`
- `GET /api/v1/recommendations/?assessment_id={assessment_uuid}`
- Documento OpenAPI actualizado.

## 3. Archivos principales

```text
app/results/routes.py
app/results/forms.py
app/results/templates/results/overview.html
app/results/templates/results/recommendations.html
app/results/templates/results/recommendation_form.html
app/results/templates/results/roadmap.html
app/services/scoring_service.py
app/services/recommendation_service.py
app/services/dashboard_service.py
app/repositories/scoring.py
app/repositories/recommendations.py
app/models/scoring.py
app/models/recommendation.py
app/static/js/results-charts.js
app/static/js/dashboard-charts.js
migrations/versions/0004_scoring_recommendations.py
```

## 4. Autorización

- El administrador puede calcular, recalcular, publicar y administrar recomendaciones.
- El revisor asignado puede previsualizar resultados y administrar recomendaciones.
- El respondedor asignado accede solo cuando los resultados están publicados.
- La API reutiliza las mismas funciones de autorización que la interfaz web.
- Los resultados de otro assessment u organización no pueden obtenerse mediante cambio de UUID.

## 5. Publicación

La publicación:

1. Valida que el assessment esté en un estado permitido.
2. Fuerza un nuevo snapshot.
3. Marca como no publicados los snapshots anteriores.
4. Marca el snapshot actual como publicado.
5. Actualiza el assessment a `published`.
6. Registra la fecha de publicación.
7. Genera auditoría.

Reabrir un assessment oculta nuevamente los resultados al respondedor hasta una nueva publicación.

## 6. Migración

La revisión `0004_scoring_recommendations` agrega campos e índices para:

- Hash de entrada.
- Resumen y metadatos del cálculo.
- Fuente e indicador de publicación indexados.
- Jerarquía, orden y metadatos de ítems.
- Dimensión de origen, fecha objetivo, orden y término de recomendaciones.

La migración mantiene las 31 tablas de la solución y es reversible.

## 7. Pruebas incluidas

- Fórmula y agregación jerárquica.
- Fuentes declarada, revisada y aprobada.
- Exclusión de “No aplica”.
- Persistencia e idempotencia de snapshots.
- Publicación de resultados.
- Acceso del respondedor antes y después de publicar.
- CRUD y generación de recomendaciones.
- Roadmap y API.
- Upgrade y downgrade de la migración 0004.

## 8. Continuidad hacia Fase 6

La Fase 6 utilizará los snapshots publicados y recomendaciones de esta fase para generar reportes web, Excel y PDF, además de incorporar backup/restore y artefactos finales de despliegue.
