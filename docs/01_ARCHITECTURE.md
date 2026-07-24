# 1. Arquitectura propuesta

## 1.1 Enfoque general

Se propone un **monolito modular con arquitectura por capas**, apropiado para el tamaño inicial del producto y preparado para evolucionar a PostgreSQL, almacenamiento de objetos y procesos asíncronos sin reescribir la lógica funcional.

La aplicación utilizará el patrón **Application Factory** de Flask y Blueprints independientes. La lógica de negocio no residirá en las vistas ni en los modelos SQLAlchemy: los controladores delegarán en servicios, y los servicios usarán repositorios y adaptadores de infraestructura.

## 1.2 Capas

### Presentación

- Blueprints Flask.
- Vistas Jinja2.
- Formularios Flask-WTF.
- API REST `/api/v1/`.
- Validación de entrada, serialización y mensajes de usuario.
- Bootstrap 5, Bootstrap Icons y Chart.js servidos localmente.

### Aplicación

- Casos de uso y orquestación transaccional.
- Servicios de assessments, revisión, scoring, evidencias, importación, reportes y auditoría.
- Reglas de autorización y transiciones de estado.
- DTOs independientes de Flask y SQLAlchemy.

### Dominio

- Estados y políticas de assessment.
- Reglas de versionamiento.
- Fórmulas de puntuación.
- Reglas de aplicabilidad y publicación.
- Políticas de revisión y trazabilidad.

### Persistencia

- SQLAlchemy 2.x.
- Repositorios por agregado.
- Migraciones con Alembic/Flask-Migrate.
- SQLite inicialmente, habilitando `PRAGMA foreign_keys=ON` y modo WAL.
- Tipos y consultas compatibles con PostgreSQL.

### Infraestructura

- Almacenamiento privado de evidencias.
- Importación y exportación Excel.
- Generación PDF y HTML.
- Auditoría estructurada.
- Adaptador antivirus preparado para ClamAV.
- Backup y restore.
- Notificaciones internas.

## 1.3 Módulos funcionales

1. **Identidad y acceso**: autenticación, roles, bloqueo, cambio obligatorio de contraseña y autorización por organización/assessment.
2. **Organizaciones**: clientes, membresías y aislamiento lógico.
3. **Catálogo SAMM**: jerarquía, preguntas, criterios, respuestas y versionamiento.
4. **Importación SAMM**: análisis, vista previa, validación, confirmación y auditoría.
5. **Assessments**: creación, asignaciones, materialización del cuestionario y estados.
6. **Respuestas**: borrador, autosave, envío, historial y snapshot.
7. **Evidencias**: carga, validación, cuarentena, descarga autorizada y trazabilidad.
8. **Revisión**: aprobar, observar, rechazar y reabrir.
9. **Scoring**: resultados por dimensión, progreso, objetivo y brechas.
10. **Recomendaciones**: priorización y roadmap.
11. **Dashboards**: administración, respondent y reviewer.
12. **Reportes**: web, Excel y PDF.
13. **API**: recursos versionados y documentación OpenAPI.
14. **Auditoría y configuración**: eventos, settings y notificaciones.

## 1.4 Despliegue objetivo

```text
Cliente Web
    │ HTTPS
    ▼
Nginx
    │ proxy_pass / archivos protegidos por endpoint autorizado
    ▼
Gunicorn
    │
    ▼
Flask modular
    ├── SQLAlchemy ── SQLite / PostgreSQL
    ├── FileStorage ── filesystem privado / object storage futuro
    ├── ReportService ── HTML / Excel / PDF
    └── AuditService ── base de datos + logs estructurados
```

## 1.5 Decisión de monolito modular

Se evita comenzar con microservicios porque:

- El dominio comparte transacciones entre respuestas, revisiones, evidencias y auditoría.
- El volumen inicial no justifica complejidad operativa adicional.
- El aislamiento modular permite extraer posteriormente reportes, archivos o notificaciones.
- Simplifica despliegue, pruebas y soporte en entornos corporativos.

## 1.6 Principios de diseño

- **Server-side rendered first**, con JavaScript progresivo.
- **Servicios sin dependencia de Flask** cuando sea posible.
- **Public IDs UUID** en URLs y API; PK internas numéricas.
- **Autorización scoped**, nunca `Model.query.get(id)` sin organización y permisos.
- **Snapshots inmutables** para evitar alteración retroactiva.
- **Soft delete** para maestros y entidades auditables.
- **UTC en persistencia**, zona horaria solo en presentación.
- **Operaciones críticas transaccionales**.
- **Configuración externa** mediante variables de entorno.
