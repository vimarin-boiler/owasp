# Contrato de importación SAMM

## Formato aceptado

Solo se aceptan archivos `.xlsx`. El archivo debe incluir las siguientes hojas:

### `imp-questions`

| Columna | Obligatoria | Descripción |
|---|---|---|
| ID | Sí | Identificador estable de la pregunta. |
| Business Function | Sí | Nombre de la función de negocio. |
| Security Practice | Sí | Nombre de la práctica. |
| Activity | Sí | Nombre del flujo o actividad. |
| Maturity | Sí | Nivel entero mayor que cero. |
| Question | Sí | Texto de la pregunta. |
| Guidance | No | Guía; cada línea no vacía se importa como criterio de calidad. |
| Answer Option | Sí | Código existente en `imp-answers`. |

### `imp-answers`

| Columna | Descripción |
|---|---|
| ANS_SET_CODE | Código del conjunto. |
| A, B, C, D | Textos de las alternativas. |
| A_W, B_W, C_W, D_W | Ponderaciones entre 0 y 1. |

## Reglas de validación

- No puede haber preguntas ni conjuntos duplicados.
- Cada pregunta debe referenciar un conjunto existente.
- Las ponderaciones deben estar entre 0 y 1 y se espera que estén ordenadas de menor a mayor.
- Un mismo código jerárquico no puede aparecer con nombres diferentes.
- El archivo se inspecciona como contenedor ZIP antes de procesar el XML interno.
- La importación se rechaza cuando faltan hojas o encabezados obligatorios.

## Detección de cambios

El sistema calcula hashes canónicos de:

- Cada conjunto de respuesta y sus alternativas.
- Cada pregunta, su jerarquía, nivel, guía, criterios y conjunto de respuesta.

Si el hash coincide con el contenido vigente, se reutiliza la revisión. Si cambia, se crea una revisión nueva y la anterior permanece intacta.

## Comandos

Validación sin aplicar el catálogo:

```bash
flask --app run.py import-samm --file data/SAMM_spreadsheet.xlsx --dry-run
```

Importación como borrador:

```bash
flask --app run.py import-samm \
  --file data/SAMM_spreadsheet.xlsx \
  --name "OWASP SAMM 2.2.0" \
  --version 2.2.0
```

Importación y publicación:

```bash
flask --app run.py import-samm \
  --file data/SAMM_spreadsheet.xlsx \
  --name "OWASP SAMM 2.2.0" \
  --version 2.2.0 \
  --publish
```
