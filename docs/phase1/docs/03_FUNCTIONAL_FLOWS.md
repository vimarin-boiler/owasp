# 3. Flujos funcionales

## 3.1 Importación inicial del catálogo

1. El administrador carga el Excel o ejecuta `flask import-samm --file ...`.
2. El archivo se copia a una ubicación temporal privada y se calcula SHA-256.
3. El parser verifica hojas y encabezados esperados.
4. Se leen `imp-questions` y `imp-answers`.
5. Se normalizan códigos, espacios, saltos de línea y tipos.
6. Se validan IDs, jerarquías, niveles, answer sets y ponderaciones.
7. Se construye una vista previa sin modificar la base de datos.
8. La UI muestra altas, coincidencias, revisiones nuevas, advertencias y errores por fila.
9. La confirmación se asocia al hash del archivo para evitar sustitución entre preview y ejecución.
10. Una única transacción crea o reutiliza jerarquías, sets, opciones, preguntas, revisiones y una versión de cuestionario.
11. Ante cualquier error bloqueante se hace rollback completo.
12. Se registra `ImportJob` y `AuditLog`.

### Estrategia idempotente

- La clave primaria funcional de pregunta es `external_code`.
- El contenido se compara mediante `content_hash`.
- Si código y hash coinciden, la fila se considera existente.
- Si el código existe con contenido distinto, se crea `QuestionRevision` nueva; nunca se sobrescribe una revisión publicada.
- Un mismo `source_sha256` confirmado no se vuelve a importar salvo uso explícito de `--force`.

## 3.2 Creación de assessment

1. Administrador selecciona organización y versión publicada.
2. Define alcance, fechas, objetivo y política de scoring.
3. Asigna respondedores y revisores.
4. El servicio valida que todos los usuarios sean miembros de la organización.
5. Se materializan las preguntas y sus snapshots.
6. El assessment pasa de draft a configured.
7. Al iniciarlo, se bloquean versión y estructura y pasa a in_progress.

## 3.3 Respuesta y autosave

1. Respondedor abre una pregunta mediante una ruta scoped al assessment asignado.
2. La UI carga texto, criterios, opciones, evidencias y observaciones.
3. Cada autosave envía un token CSRF y `row_version`.
4. El servicio verifica ownership, estado y concurrencia.
5. Se guarda borrador, incrementa versión y genera historial cuando cambia contenido relevante.
6. La carga de evidencia se realiza en una operación independiente y autorizada.
7. Al enviar, se verifica respuesta completa o justificación N/A.
8. El estado cambia a submitted y queda bloqueada para el respondedor.

## 3.4 Revisión

1. Revisor accede solo a assessments asignados.
2. Visualiza respuesta, criterios y evidencias.
3. Puede aprobar, observar o rechazar.
4. La decisión crea un `Review`, actualiza el estado y registra auditoría.
5. En observada/rechazada, el respondedor recupera edición y recibe notificación.
6. Al reenviar se crea una nueva versión de respuesta.
7. El administrador o revisor puede reabrir una aprobada antes de publicación, indicando motivo.

## 3.5 Publicación de resultados

1. El sistema verifica que todas las preguntas requeridas estén aprobadas o N/A aprobadas.
2. Se calcula un snapshot de resultados.
3. El assessment pasa a completed.
4. El administrador revisa recomendaciones y roadmap.
5. Al publicar, se fija el snapshot publicado y se habilita visualización al respondedor.
6. Los reportes publicados apuntan a ese snapshot.
7. Reabrir después de publicar requiere revocar publicación con motivo, crear nuevo ciclo y conservar el snapshot anterior.

## 3.6 Evidencias

1. El usuario selecciona archivo y descripción.
2. Se valida cantidad y tamaño antes de persistir.
3. Se genera nombre UUID y se escribe en cuarentena.
4. Se valida extensión, MIME detectado y firma conocida cuando aplique.
5. Se rechazan ejecutables, scripts, dobles extensiones peligrosas y formatos no permitidos.
6. Se calcula SHA-256.
7. El adaptador antivirus retorna clean, infected, error o pending.
8. Solo archivos clean pasan al storage definitivo.
9. La descarga exige autorización contextual y usa `Content-Disposition: attachment`.
10. Carga, descarga, revisión y eliminación lógica se auditan.

## 3.7 Backup y restore

### Backup

- Activa modo de mantenimiento lógico para operaciones críticas.
- Usa la API de backup consistente de SQLite.
- Copia evidencias activas.
- Genera `manifest.json` con versión, fecha, tamaños y hashes.
- Empaqueta en ZIP y calcula hash final.

### Restore

- Extrae en staging con protección anti Zip Slip.
- Valida manifest y todos los hashes.
- Verifica versión y migraciones compatibles.
- Detiene escrituras.
- Reemplaza de forma atómica base y storage.
- Ejecuta validaciones de integridad y registra auditoría.
