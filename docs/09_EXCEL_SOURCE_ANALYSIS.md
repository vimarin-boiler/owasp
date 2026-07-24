# 9. Análisis del archivo SAMM_spreadsheet.xlsx

## 9.1 Estructura encontrada

El workbook contiene 12 hojas:

1. Attribution and License
2. Getting Started
3. Benchmark
4. Interview
5. Scorecard
6. Roadmap
7. Roadmap Chart
8. Lookups
9. imp-questions
10. DV-Lists
11. imp-answers
12. Background Images

## 9.2 Fuente canónica para importación

### imp-questions

Columnas:

- `ID`
- `Business Function`
- `Security Practice`
- `Activity`
- `Maturity`
- `Question`
- `Guidance`
- `Answer Option`

Resultados de validación:

- 90 preguntas.
- 5 funciones de negocio.
- 15 prácticas.
- 30 flujos.
- Niveles 1, 2 y 3.
- 18 preguntas por función.
- 6 preguntas por práctica.
- 3 preguntas por flujo, una por nivel.
- Cero IDs duplicados.
- Cero campos obligatorios vacíos.
- Todos los códigos de answer set referenciados existen.

### imp-answers

Columnas:

- `ANS_SET_CODE`
- `A`, `B`, `C`, `D`
- `A_W`, `B_W`, `C_W`, `D_W`

Resultados:

- 24 answer sets.
- Cuatro alternativas por set.
- Ponderaciones típicas: 0, 0.25, 0.5 y 1.
- Los 24 sets son utilizados por al menos una pregunta.

## 9.3 Mapeo de importación

| Excel | Entidad destino |
|---|---|
| ID | Question.external_code |
| Business Function | BusinessFunction |
| Security Practice | SecurityPractice |
| Activity | PracticeStream |
| Maturity | MaturityLevel |
| Question | QuestionRevision.question_text |
| Guidance | QuestionQualityCriterion por línea + guidance_text completo |
| Answer Option | AnswerSet.external_code |
| ANS_SET_CODE | AnswerSet.external_code |
| A-D | AnswerOption.text |
| A_W-D_W | AnswerOption.weight |

## 9.4 Convención observada de IDs

Ejemplo: `G-SM-A-1-1`

```text
G   = función Governance
SM  = práctica Strategy and Metrics
A   = flujo A
1   = nivel de madurez
1   = ordinal de pregunta dentro del nivel
```

El modelo no dependerá de esta convención para funcionar, pero la conservará como código externo.

## 9.5 Jerarquía resumida

- Governance: Strategy and Metrics, Policy and Compliance, Education and Guidance.
- Design: Threat Assessment, Security Requirements, Secure Architecture.
- Implementation: Secure Build, Secure Deployment, Defect Management.
- Verification: Architecture Assessment, Requirements-driven Testing, Security Testing.
- Operations: Incident Management, Environment Management, Operational Management.

Cada práctica contiene dos flujos y cada flujo tres niveles en el archivo actual.

## 9.6 Validaciones del importador

El importador deberá rechazar o advertir:

- Hojas o encabezados ausentes.
- IDs duplicados en el mismo archivo.
- Jerarquías inconsistentes para un mismo código.
- Nivel no numérico o inexistente.
- Answer set no encontrado.
- Ponderación fuera de rango.
- Alternativas vacías o duplicadas.
- Guidance vacío cuando la política lo requiera.
- Código existente con contenido distinto, tratándolo como revisión nueva.
