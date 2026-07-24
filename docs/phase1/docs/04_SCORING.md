# 4. Modelo de puntuación

## 4.1 Observación del Excel fuente

El archivo utiliza alternativas con ponderaciones entre 0 y 1. Cuando las tres preguntas de nivel de un flujo tienen peso 1, el flujo alcanza 3. El score de práctica y función se obtiene mediante agregación de sus componentes.

La implementación mantendrá esta semántica, pero sin depender de cantidades fijas.

## 4.2 Fórmulas

### Puntaje de pregunta

```text
question_score = selected_option_weight
```

Una respuesta ausente o que no cumple el estado requerido por la política de scoring aporta 0. Una pregunta N/A aceptada se excluye del denominador.

### Puntaje de nivel dentro de un flujo

```text
level_score = sum(question_score) / applicable_questions_in_level
```

- Preguntas pendientes siguen siendo aplicables y aportan 0.
- Solo N/A válido se excluye.
- Si no hay preguntas aplicables en un nivel, el nivel se marca `not_applicable` y no se usa para el porcentaje normalizado.

### Puntaje de flujo

```text
stream_score = sum(level_score for each defined maturity level)
stream_max = sum(max_score for each defined maturity level)
```

Con tres niveles de máximo 1, el rango es 0 a 3.

### Puntaje de práctica

```text
practice_score = weighted_average(stream_scores)
```

Por defecto los flujos pesan igual. La arquitectura permite pesos futuros.

### Puntaje de función

```text
function_score = weighted_average(practice_scores)
```

### Puntaje general

```text
overall_score = weighted_average(function_scores)
```

Por defecto las cinco funciones pesan igual.

### Porcentaje normalizado

```text
normalized_percent = earned_points / applicable_max_points * 100
```

El máximo aplicable excluye únicamente preguntas N/A válidas, nunca preguntas pendientes.

### Brecha

```text
gap = max(target_score - current_score, 0)
```

## 4.3 Fuentes de resultado configurables

### Declared

Usa la respuesta declarada por el respondedor, aunque aún no esté revisada.

### Reviewed

Usa respuestas que ya tienen decisión de revisión. Observadas o rechazadas aportan 0 hasta ser corregidas.

### Approved

Solo usa respuestas aprobadas. Es la fuente recomendada para publicación oficial.

La condición de N/A sigue la misma fuente: un N/A declarado puede excluirse en modo declared, pero en modo approved solo se excluye después de ser aprobado.

## 4.4 Progreso

Se expondrán al menos dos indicadores:

```text
response_progress = preguntas completas o N/A declaradas / preguntas requeridas
review_progress = preguntas aprobadas o N/A aprobadas / preguntas requeridas
```

No se mezclará avance con score; una respuesta pendiente puede reducir score pero no debe contarse como progreso.

## 4.5 Versionamiento del motor

Cada snapshot almacenará `calculation_version`, por ejemplo `samm-score-v1`. Cambios futuros de fórmula crearán una nueva versión sin recalcular silenciosamente reportes históricos.
