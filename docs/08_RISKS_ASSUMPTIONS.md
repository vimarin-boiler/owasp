# 8. Riesgos y supuestos

## 8.1 Supuestos adoptados

1. El archivo entregado es la fuente inicial y corresponde a la versión indicada internamente como SAMM v2.2.0.
2. La hoja `imp-questions` es la fuente canónica de preguntas.
3. La hoja `imp-answers` es la fuente canónica de alternativas y ponderaciones.
4. Cada línea no vacía de `Guidance` representa un criterio de calidad.
5. Los códigos de pregunta son estables y únicos.
6. La ponderación de cada alternativa se encuentra entre 0 y 1.
7. El score de flujo se expresa en la suma de niveles; con tres niveles, su máximo es 3.
8. Los usuarios pueden pertenecer a más de una organización.
9. Un assessment usa una única versión de cuestionario durante toda su vida.
10. Las evidencias se almacenarán inicialmente en el filesystem del servidor.
11. Los resultados publicados deben ser reproducibles e inmutables.
12. La aplicación se ejecutará detrás de Nginx con TLS en producción.

## 8.2 Riesgos

| Riesgo | Impacto | Mitigación |
|---|---:|---|
| SQLite con múltiples escrituras concurrentes | Alto | WAL, transacciones breves, timeout y camino documentado a PostgreSQL. |
| Edición de catálogo histórico | Alto | Revisiones inmutables, versiones publicadas bloqueadas y snapshots. |
| IDOR entre clientes | Crítico | Scoping por organización, UUID públicos y pruebas de autorización cruzada. |
| Malware en evidencias | Crítico | Cuarentena, detección MIME, ClamAV adapter y descarga forzada. |
| Archivos ZIP maliciosos | Alto | No extraer en carga, límites de compresión y validación adicional. |
| Score inflado por preguntas pendientes | Alto | Pendientes permanecen en denominador; solo N/A válido se excluye. |
| Diferencias de interpretación SAMM | Medio | Motor versionado, fórmulas documentadas y fixtures derivados del Excel. |
| PDF inconsistente con dashboard | Medio | Generar desde snapshot de score y gráficos server-side. |
| Importación con contenido alterado | Alto | SHA-256, preview ligada al hash y transacción única. |
| Datos sensibles en logs | Alto | Sanitización central, allowlist de campos y pruebas. |
| Restauración corrupta | Crítico | Staging, manifest, hashes, backup previo y reemplazo atómico. |
| Dependencias frontend externas bloqueadas | Medio | Vendorizar assets localmente. |
| Crecimiento de evidencias | Medio | Cuotas, retención, storage backend y futura migración a object storage. |

## 8.3 Temas a confirmar antes de Fase 2

No bloquean el diseño, pero deben quedar configurables:

- Si un administrador es global o limitado por organización.
- Si N/A debe requerir siempre aprobación de revisor.
- Peso igual o configurable entre funciones/prácticas/flujos.
- Idioma inicial del catálogo y estrategia de traducción.
- Retención de evidencias y backups.
- Tipos de documento corporativo permitidos adicionales.
- Si el rol reviewer puede publicar resultados o solo recomendar publicación.
