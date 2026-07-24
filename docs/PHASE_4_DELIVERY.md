# Entrega Fase 4 — Ejecución del assessment

## Objetivo

Implementar el ciclo operativo completo de un assessment OWASP SAMM sobre el catálogo versionado: creación, asignación, respuesta, evidencia, revisión y cierre funcional.

## Alcance entregado

### Organizaciones y assessments

- Selección de organización activa.
- Selección exclusiva de versiones publicadas.
- Nombre, descripción, alcance, fechas y nivel objetivo.
- Fuente de scoring preparada para declarado, revisado o aprobado.
- Estados de assessment con transiciones controladas.
- Asignación de múltiples respondedores y revisores.

### Instanciación histórica

Cada `AssessmentQuestion` conserva snapshots de:

- Código y texto de la pregunta.
- Guidance.
- Criterios de calidad.
- Alternativas, textos, pesos y orden.
- Función, práctica y flujo.
- Nivel de madurez.
- Obligatoriedad y orden.

Esto impide que un cambio futuro en el catálogo modifique resultados históricos.

### Cuestionario

- Navegación jerárquica.
- Filtros por función, práctica, flujo y estado.
- Búsqueda por código o texto.
- Indicadores de progreso.
- Pregunta anterior y siguiente.
- Aviso de cambios sin guardar.
- Autosave configurable.

### Respuestas

- Borrador.
- Respondida.
- Enviada.
- Observada.
- Rechazada.
- Aprobada.
- Marcación No aplica con justificación.
- Copia histórica de alternativa, texto y ponderación.
- Versión incremental e historial de transiciones.

### Revisión

- Cola de respuestas enviadas.
- Aprobación, observación y rechazo.
- Comentario obligatorio para observar o rechazar.
- Reapertura de respuestas aprobadas.
- Validación individual de evidencias.
- Observaciones generales del assessment.
- Notificaciones internas.

### Evidencias

- Carga múltiple.
- Archivos privados.
- Hash SHA-256.
- Validación de firma, formato y contenido comprimido.
- Prevención de duplicados.
- Descarga y eliminación autorizadas.
- Trazabilidad de revisión.
- Contrato para scanner antivirus.

### API

Se añadieron endpoints autenticados para:

- Listar assessments autorizados.
- Consultar detalle y progreso.
- Consultar preguntas instanciadas.
- Guardar o enviar respuestas.
- Consultar metadatos de evidencias.

## Archivos principales

```text
app/assessments/routes.py
app/assessments/forms.py
app/services/assessment_service.py
app/services/response_service.py
app/services/review_service.py
app/services/evidence_service.py
app/common/assessment_access.py
app/repositories/assessments.py
app/models/assessment.py
app/models/response.py
app/models/evidence.py
migrations/versions/0003_assessment_workflow.py
```

## Criterios de aceptación cubiertos

- Crear organización y assessment.
- Asignar usuarios.
- Restringir assessments al usuario asignado.
- Responder y guardar borradores.
- Adjuntar evidencias.
- Enviar a revisión.
- Aprobar, observar, rechazar y reabrir.
- Proteger archivos por autorización.
- Auditar acciones relevantes.

Los resultados consolidados, gráficos de madurez y reportes corresponden a las Fases 5 y 6.
