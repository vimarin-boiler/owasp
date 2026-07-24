# Versionamiento del catálogo

## Principios

1. Un identificador de pregunta representa la identidad lógica de la pregunta.
2. El contenido editable se almacena en revisiones numeradas.
3. Editar una pregunta crea una revisión nueva; nunca sobrescribe una revisión existente.
4. Una versión de cuestionario enlaza revisiones concretas y ordenadas.
5. Los assessments de la Fase 4 se vincularán permanentemente a una versión.
6. Los conjuntos de respuesta utilizados no pueden editarse; debe crearse un conjunto nuevo.
7. Los nombres y códigos jerárquicos utilizados por revisiones se consideran estructuralmente inmutables.

## Estados

### Revisión de pregunta

- `draft`
- `published`
- `archived`

### Versión de cuestionario

- `draft`
- `published`
- `archived`

Al publicar una versión:

- Las revisiones en borrador vinculadas pasan a publicadas.
- La versión publicada anterior pasa a archivada.
- Las versiones archivadas permanecen disponibles para trazabilidad y assessments históricos.

## Reimportación

Una nueva importación puede producir tres resultados por pregunta:

- **Sin cambio:** se reutiliza la revisión vigente.
- **Contenido modificado:** se crea la siguiente revisión.
- **Pregunta nueva:** se crea la identidad y la revisión 1.

La comparación incluye el hash del conjunto de respuestas para detectar cambios en alternativas o ponderaciones.
