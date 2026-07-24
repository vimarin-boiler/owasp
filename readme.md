# NTT DevSecOps Assessment — Fase 1: Diseño

Este paquete contiene el diseño técnico y funcional de una plataforma web para administrar y ejecutar assessments de madurez DevSecOps basados en OWASP SAMM.

## Alcance de esta entrega

La Fase 1 incluye:

- Arquitectura lógica y física propuesta.
- Modelo de datos y relaciones.
- Diagrama entidad-relación.
- Flujos funcionales y máquinas de estado.
- Estructura completa del proyecto.
- Decisiones de diseño y seguridad.
- Riesgos, supuestos y mitigaciones.
- Análisis verificable del archivo `SAMM_spreadsheet.xlsx`.
- Plan de implementación para las fases posteriores.

No incluye todavía el código ejecutable de Flask. Ese código comienza en la Fase 2, usando este diseño como contrato técnico.

## Documento principal

Abrir [`docs/PHASE_1_DESIGN.md`](docs/PHASE_1_DESIGN.md).

## Diagramas

- [`diagrams/architecture.svg`](diagrams/architecture.svg)
- [`diagrams/erd.svg`](diagrams/erd.svg)
- [`diagrams/assessment_state.svg`](diagrams/assessment_state.svg)
- [`diagrams/response_state.svg`](diagrams/response_state.svg)
- [`diagrams/import_flow.svg`](diagrams/import_flow.svg)

## Fuente analizada

El análisis estructural se encuentra en [`data/source_excel_analysis.json`](data/source_excel_analysis.json).
