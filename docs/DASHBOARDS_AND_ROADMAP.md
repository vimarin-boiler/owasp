# Dashboards, brechas, recomendaciones y roadmap

## 1. Dashboard administrativo

El dashboard administrativo combina información operativa y de madurez:

- Assessments totales, activos y completados.
- Organizaciones y usuarios activos.
- Avance promedio.
- Respuestas pendientes de revisión.
- Evidencias pendientes de validación.
- Assessments con fecha objetivo dentro de los próximos 14 días.
- Promedio de madurez por función.
- Promedio de madurez por práctica.
- Brechas de práctica más relevantes.
- Distribución de assessments por rango de avance.
- Actividad reciente de auditoría.

Para proteger el rendimiento, la consolidación de resultados limita la muestra de cálculo en vivo a los primeros 40 assessments no borrador ni cancelados. En una futura operación de gran escala debe reemplazarse por materialización o jobs programados.

## 2. Dashboard del respondedor

Muestra exclusivamente assessments asignados y resume:

- Cantidad asignada.
- Preguntas pendientes.
- Observadas.
- Rechazadas.
- Aprobadas.
- Avance por assessment.
- Fecha objetivo.
- Última actividad.

## 3. Resultados del assessment

La vista de resultados incluye:

- Puntaje general.
- Nivel objetivo y brecha.
- Avance.
- Fuente de scoring.
- Fecha y número de snapshot.
- Resumen de estados.
- Evidencias.
- Radar por función.
- Barras por práctica.
- Distribución de estados.
- Comparación actual versus objetivo.
- Tabla de funciones.
- Matriz de brechas por práctica y flujo.

Los datos para gráficos se generan en servidor y se exponen como atributos JSON escapados. La ejecución se realiza desde archivos JavaScript separados para respetar la CSP.

## 4. Visibilidad

| Rol | Durante ejecución | Después de publicar |
|---|---:|---:|
| Administrador | Sí | Sí |
| Revisor asignado | Sí | Sí |
| Respondedor asignado | No | Sí |
| Usuario no asignado | No | No |

## 5. Recomendaciones

Una recomendación puede asociarse a:

- Función.
- Práctica.
- Flujo.
- Pregunta.

Campos principales:

- Título y descripción.
- Riesgo.
- Prioridad.
- Esfuerzo.
- Responsable sugerido.
- Horizonte y fecha objetivo.
- Dependencias.
- Estado.
- Quick win.
- Nivel objetivo.

No se elimina físicamente: se desactiva para conservar trazabilidad.

## 6. Generación desde brechas

La generación automática inicial:

1. Recalcula y persiste un snapshot.
2. Selecciona brechas de práctica iguales o superiores a 0.25.
3. Ordena de mayor a menor brecha.
4. Genera hasta 15 recomendaciones.
5. Asigna prioridad según magnitud.
6. Sugiere horizonte y quick win de acuerdo con la brecha.
7. Evita duplicados activos para la misma dimensión.
8. Registra auditoría.

Las recomendaciones generadas son un punto de partida y deben ser refinadas por el consultor o revisor.

## 7. Roadmap

Horizontes soportados:

- 0 a 30 días.
- 31 a 90 días.
- 3 a 6 meses.
- 6 a 12 meses.
- Sin horizonte.

Cada tarjeta muestra prioridad, estado, responsable, esfuerzo, fecha objetivo, quick win y dimensión asociada.

## 8. Chart.js

`CHART_JS_URL` permite elegir una ruta externa versionada o un archivo local. La CSP permite el origen predeterminado `cdn.jsdelivr.net`. Un dominio externo diferente requiere ajustar la política. Para entornos aislados se recomienda copiar el archivo a `app/static/vendor/` y usar una ruta servida por la aplicación.

## 9. Consideraciones de rendimiento

- Los resultados publicados se leen desde snapshots.
- Los resultados de previsualización se calculan bajo demanda.
- Los snapshots con el mismo hash pueden reutilizarse.
- Los índices cubren assessment, fuente, publicación, dimensión, prioridad, estado y horizonte.
- Para grandes volúmenes conviene añadir cache, cálculo asíncrono y agregados materializados en una fase posterior.
