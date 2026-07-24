# Metodología de puntuación SAMM

## 1. Propósito

El motor convierte respuestas ponderadas en resultados comparables de madurez. El cálculo no modifica respuestas ni el catálogo: consume snapshots del assessment y produce snapshots independientes de resultados.

## 2. Escala

- Pregunta: 0 a 1.
- Nivel: 0 a 1.
- Flujo: 0 a 3.
- Práctica: 0 a 3.
- Función: 0 a 3.
- Assessment: 0 a 3.

La versión inicial de la fórmula es:

```text
samm-3-level-v1
```

## 3. Fuentes

### Declarada (`declared`)

Una respuesta es elegible cuando está:

- Respondida.
- Enviada a revisión.
- Observada.
- Rechazada.
- Aprobada.

Permite observar la postura informada por el respondedor.

### Revisada (`reviewed`)

Una respuesta es elegible cuando posee fecha de revisión y está:

- Observada.
- Rechazada.
- Aprobada.

Permite analizar la postura que ya pasó por revisión, aunque requiera correcciones.

### Aprobada (`approved`)

Solo considera respuestas aprobadas. Es la fuente más conservadora y apropiada para una publicación final validada.

## 4. Valor por pregunta

La ponderación seleccionada se toma del snapshot de la respuesta y se limita al rango 0–1.

```text
question_score = clamp(selected_weight_snapshot, 0, 1)
```

Una respuesta no elegible obtiene cero y se considera pendiente.

## 5. No aplica

Una pregunta marcada “No aplica” se excluye del denominador únicamente cuando la respuesta es elegible para la fuente seleccionada.

Esto evita dos distorsiones:

- No castiga una exclusión validada por aplicabilidad.
- No permite que una pregunta pendiente se elimine del denominador simplemente por contener una marca todavía no elegible.

Cuando todas las preguntas de un nivel son no aplicables, ese nivel no aporta al denominador del flujo.

## 6. Nivel

Para cada combinación función–práctica–flujo–nivel:

```text
level_score = sum(question_score applicable) / applicable_questions
```

Su máximo es 1.

Las preguntas aplicables pendientes permanecen en el denominador con valor cero. Por ello, el resultado representa tanto el nivel demostrado como la falta de respuestas válidas.

## 7. Flujo

Los niveles aplicables del flujo se normalizan a 0–3:

```text
stream_score = average(applicable_level_scores) * 3
```

La normalización permite comparar flujos incluso si un nivel completo quedó fuera de alcance.

## 8. Práctica

```text
practice_score = average(applicable_stream_scores)
```

## 9. Función

```text
function_score = average(applicable_practice_scores)
```

## 10. Resultado general

```text
overall_score = average(applicable_function_scores)
```

Si no existen funciones aplicables, el resultado es 0.

## 11. Objetivo y brecha

El nivel objetivo se guarda en el assessment dentro del rango 0–3.

Para flujo, práctica, función y assessment:

```text
gap = max(target_score - current_score, 0)
```

Para cada nivel, el objetivo parcial se obtiene así:

```text
target_for_level = clamp(target - (level_number - 1), 0, 1)
```

Ejemplo con objetivo 2.5:

- Nivel 1: 1.0.
- Nivel 2: 1.0.
- Nivel 3: 0.5.

## 12. Progreso

El progreso es independiente de la madurez. Se calcula sobre todas las preguntas instanciadas del assessment y representa el porcentaje que alcanzó un estado que evidencia trabajo realizado.

El snapshot también conserva:

- Conteos por estado.
- Aplicables y no aplicables.
- Pendientes para la fuente.
- Aprobadas, observadas y rechazadas.
- Resumen de evidencias.

## 13. Reproducibilidad

El hash de entrada incluye:

- Versión de fórmula.
- Assessment.
- Fuente.
- Nivel objetivo.
- Identificador y obligatoriedad de cada pregunta.
- Nivel de madurez.
- Estado y versión de respuesta.
- Ponderación seleccionada.
- Indicador de no aplicabilidad.
- Fecha de revisión.

La representación se serializa de forma canónica y se procesa con SHA-256.

## 14. Snapshots

Un snapshot contiene el resultado general y un conjunto de ítems jerárquicos:

```text
assessment
└── function
    └── practice
        └── stream
            └── level
                └── question
```

Cada ítem conserva clave, padre, orden, metadatos, puntaje, máximo, porcentaje normalizado, objetivo, brecha y conteos.

## 15. Decisiones de diseño

- Las preguntas pendientes no se ignoran.
- La aplicabilidad no se infiere automáticamente.
- No se promedia directamente el total de preguntas de toda la organización, porque eso sobrerrepresentaría prácticas con más preguntas.
- La agregación respeta la jerarquía SAMM.
- Los snapshots no se recalculan retroactivamente.
- Una futura fórmula debe usar un nuevo identificador de versión.
