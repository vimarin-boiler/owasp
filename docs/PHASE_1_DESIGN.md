# Diseño de plataforma NTT DevSecOps Assessment

**Fase 1 — Arquitectura, modelo y decisiones**

## Resumen ejecutivo

La solución se implementará como un monolito modular Flask, con separación entre presentación, servicios de aplicación, reglas de dominio, repositorios e infraestructura. La base inicial será SQLite, pero las consultas, tipos y transacciones se diseñarán para migrar a PostgreSQL sin modificar la lógica funcional.

El elemento central del diseño es la inmutabilidad histórica: el catálogo usa revisiones y versiones publicadas; cada assessment materializa un snapshot completo de sus preguntas; cada cambio de respuesta crea historial; y los resultados oficiales se almacenan como snapshots versionados.

El análisis del Excel confirmó una fuente consistente: 90 preguntas, 5 funciones, 15 prácticas, 30 flujos, 3 niveles y 24 conjuntos de respuestas, sin IDs duplicados ni campos obligatorios vacíos.

## Documentos de esta fase

1. [Arquitectura propuesta](01_ARCHITECTURE.md)
2. [Modelo de datos](02_DATA_MODEL.md)
3. [Flujos funcionales](03_FUNCTIONAL_FLOWS.md)
4. [Modelo de puntuación](04_SCORING.md)
5. [Estructura completa del proyecto](05_PROJECT_STRUCTURE.md)
6. [Diseño de seguridad](06_SECURITY_DESIGN.md)
7. [Decisiones de diseño](07_DECISIONS.md)
8. [Riesgos y supuestos](08_RISKS_ASSUMPTIONS.md)
9. [Análisis del Excel](09_EXCEL_SOURCE_ANALYSIS.md)
10. [Plan de implementación](10_IMPLEMENTATION_PLAN.md)

## Diagramas

- [Arquitectura lógica](../diagrams/architecture.svg)
- [Modelo entidad-relación](../diagrams/erd.svg)
- [Estados del assessment](../diagrams/assessment_state.svg)
- [Estados de respuesta](../diagrams/response_state.svg)
- [Flujo de importación](../diagrams/import_flow.svg)

## Resultado de la Fase 1

El diseño queda cerrado como base para la Fase 2. Las decisiones más importantes son:

- Versionamiento inmutable de preguntas y cuestionarios.
- Snapshot de preguntas y opciones dentro de cada assessment.
- N/A separado del estado de workflow y sujeto a revisión.
- Scoring versionado con pendientes en el denominador y N/A válido excluido.
- Aislamiento multi-organización y protección contra IDOR desde repositorios y servicios.
- Evidencias en storage privado con cuarentena, hash y antivirus extensible.
- Resultados publicados como snapshots reproducibles.
