# 7. Decisiones principales de diseño

## ADR-001 — Monolito modular

**Decisión:** una sola aplicación Flask con módulos claramente separados.

**Motivo:** preserva transacciones, reduce complejidad operativa y permite extracción futura.

## ADR-002 — Question + QuestionRevision

**Decisión:** separar identidad estable y contenido inmutable.

**Motivo:** una pregunta usada por una versión publicada no debe modificarse retroactivamente.

## ADR-003 — Materialización de AssessmentQuestion

**Decisión:** copiar texto, jerarquía, criterios y opciones al crear el assessment.

**Motivo:** garantiza reproducibilidad incluso si el catálogo evoluciona.

## ADR-004 — Historial append-only

**Decisión:** guardar cada versión de respuesta y cada revisión como evento inmutable.

**Motivo:** trazabilidad completa y reportes históricos confiables.

## ADR-005 — N/A como atributo y workflow como estado

**Decisión:** `is_not_applicable` es ortogonal al estado de revisión.

**Motivo:** un N/A también debe enviarse, justificarse y aprobarse. La UI podrá mostrar “N/A pendiente” o “N/A aprobado” sin perder el estado real.

## ADR-006 — Snapshot de scoring publicado

**Decisión:** persistir resultados oficiales en lugar de recalcularlos siempre.

**Motivo:** evita que cambios de fórmula o configuración alteren reportes emitidos.

## ADR-007 — UUID público + PK numérica

**Decisión:** usar PK enteras para eficiencia y UUID para exposición externa.

**Motivo:** reduce enumeración sin confundirlo con autorización.

## ADR-008 — Almacenamiento por interfaz

**Decisión:** `StorageBackend` con implementación local inicial.

**Motivo:** migración posterior a S3/Azure Blob sin cambiar servicios.

## ADR-009 — Excel importado como draft

**Decisión:** una importación crea una versión draft que debe ser publicada explícitamente.

**Motivo:** permite revisar advertencias antes de usarla en assessments.

## ADR-010 — Dependencias frontend locales

**Decisión:** Bootstrap, Icons y Chart.js se almacenan en `static/vendor`.

**Motivo:** CSP más estricta, operación en redes restringidas y menor dependencia de CDN.

## ADR-011 — PDF con HTML/CSS y gráficos estáticos

**Decisión:** WeasyPrint para PDF y gráficos SVG/PNG generados en servidor.

**Motivo:** Chart.js usa canvas del navegador y no es confiable para PDF headless sin procesamiento adicional.

## ADR-012 — Sin tareas asíncronas en el MVP

**Decisión:** importaciones de 90 preguntas y reportes iniciales se ejecutan síncronamente con límites y estado.

**Motivo:** evita Celery/Redis prematuros. Se conserva una interfaz de jobs para migrar cuando el volumen lo requiera.
