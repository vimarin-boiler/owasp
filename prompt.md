Actúa como un arquitecto de software, desarrollador senior Python, especialista en aplicaciones web seguras, UX/UI y DevSecOps.

Necesito que diseñes y desarrolles una aplicación web completa para administrar y ejecutar assessments de madurez DevSecOps basados en OWASP SAMM.

Usa como fuente inicial de información el archivo Excel adjunto:

`SAMM_spreadsheet.xlsx`

El archivo contiene las funciones de negocio, prácticas de seguridad, flujos, niveles de madurez, preguntas, criterios de calidad, posibles respuestas y ponderaciones del cuestionario OWASP SAMM.

# 1. Objetivo del sistema

Construir una plataforma web que permita:

1. Administrar el catálogo de preguntas OWASP SAMM.
2. Crear assessments para distintas organizaciones o clientes.
3. Asignar usuarios responsables de responder cada assessment.
4. Permitir que los usuarios respondan las preguntas.
5. Adjuntar una o más evidencias en cada pregunta.
6. Guardar toda la información en una base de datos SQLite.
7. Calcular automáticamente los resultados de madurez.
8. Mostrar dashboards, indicadores, gráficos y brechas.
9. Mantener trazabilidad y auditoría de todas las acciones.
10. Generar reportes de resultados y recomendaciones.

# 2. Stack tecnológico obligatorio

La solución deberá utilizar:

* Python 3.12 o superior.
* Flask como framework backend.
* SQLAlchemy como ORM.
* Flask-Migrate y Alembic para migraciones.
* Flask-Login para autenticación.
* Flask-WTF para formularios y protección CSRF.
* Jinja2 para renderizado de vistas.
* SQLite como base de datos inicial.
* Bootstrap 5 para el frontend.
* JavaScript moderno, evitando dependencias innecesarias.
* Chart.js para gráficos y dashboards.
* Bootstrap Icons para iconografía.
* pytest para pruebas automatizadas.
* Gunicorn para ejecución en producción Linux.
* Nginx como reverse proxy en producción.

La aplicación deberá quedar preparada para que SQLite pueda ser reemplazado posteriormente por PostgreSQL sin modificar la lógica funcional.

# 3. Arquitectura esperada

Implementa una arquitectura modular, mantenible y escalable.

Usa una estructura similar a:

```text
samm_assessment/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models/
│   ├── services/
│   ├── repositories/
│   ├── forms/
│   ├── auth/
│   ├── admin/
│   ├── assessments/
│   ├── dashboard/
│   ├── reports/
│   ├── api/
│   ├── templates/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   ├── img/
│   │   └── icons/
│   └── utils/
├── migrations/
├── uploads/
├── instance/
├── tests/
├── scripts/
├── config.py
├── run.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

Separa claramente:

* Modelos de datos.
* Repositorios.
* Servicios de negocio.
* Controladores o blueprints.
* Formularios.
* Plantillas.
* Validaciones.
* Gestión de archivos.
* Cálculo de resultados.
* Generación de reportes.

No concentres toda la lógica en un único archivo.

# 4. Roles de usuario

Implementa control de acceso basado en roles.

## 4.1. Administrador

El administrador podrá:

* Crear, editar, activar y desactivar usuarios.
* Restablecer contraseñas.
* Asignar roles.
* Crear organizaciones o clientes.
* Crear nuevos assessments.
* Editar información de un assessment.
* Asignar usuarios respondedores.
* Administrar funciones de negocio.
* Administrar prácticas.
* Administrar flujos o subcategorías.
* Administrar niveles de madurez.
* Crear, editar, ordenar, activar o desactivar preguntas.
* Administrar alternativas de respuesta.
* Administrar ponderaciones.
* Administrar criterios de calidad.
* Importar preguntas desde el archivo Excel.
* Exportar el cuestionario a Excel.
* Revisar respuestas.
* Revisar evidencias.
* Aprobar, rechazar u observar respuestas.
* Reabrir preguntas.
* Cerrar assessments.
* Consultar resultados globales.
* Descargar reportes.
* Consultar la bitácora de auditoría.

## 4.2. Respondedor

El usuario respondedor podrá:

* Acceder solamente a los assessments que tenga asignados.
* Visualizar el avance de sus assessments.
* Navegar por función, práctica, flujo y nivel.
* Responder las preguntas habilitadas.
* Seleccionar una de las respuestas permitidas.
* Agregar comentarios o justificaciones.
* Subir una o más evidencias por pregunta.
* Eliminar evidencias propias mientras la pregunta no esté enviada.
* Guardar respuestas como borrador.
* Enviar una pregunta para revisión.
* Consultar observaciones del administrador.
* Corregir respuestas rechazadas u observadas.
* Consultar el estado general del assessment.
* Visualizar resultados únicamente cuando el administrador los publique.

## 4.3. Revisor opcional

Deja preparado un rol revisor que pueda:

* Revisar respuestas.
* Validar evidencias.
* Agregar observaciones.
* Aprobar o rechazar respuestas.
* No modificar el catálogo global de preguntas ni administrar usuarios.

# 5. Modelo funcional del assessment

Cada assessment deberá estar asociado a:

* Una organización o cliente.
* Un nombre.
* Una descripción.
* Un alcance.
* Una fecha de inicio.
* Una fecha objetivo.
* Un estado.
* Uno o más usuarios respondedores.
* Uno o más revisores.
* Una versión del cuestionario.
* Un nivel de madurez objetivo opcional.

Estados sugeridos:

* Borrador.
* Configurado.
* En ejecución.
* En revisión.
* Con observaciones.
* Completado.
* Publicado.
* Cerrado.
* Cancelado.

Cada pregunta dentro del assessment deberá tener su propio estado:

* Sin responder.
* Borrador.
* Respondida.
* Enviada a revisión.
* Observada.
* Rechazada.
* Aprobada.
* No aplica.

# 6. Estructura del cuestionario

El sistema deberá preservar la jerarquía del archivo Excel:

```text
Función de negocio
└── Práctica de seguridad
    └── Flujo o subcategoría
        └── Nivel de madurez
            └── Pregunta
                ├── Criterios de calidad
                ├── Respuestas posibles
                └── Ponderación
```

Como referencia, el cuestionario OWASP SAMM contiene:

* 5 funciones de negocio.
* 15 prácticas de seguridad.
* 30 flujos.
* 3 niveles de madurez.
* Preguntas, criterios de calidad y conjuntos de respuestas ponderadas.

El sistema no debe depender de cantidades fijas. El administrador deberá poder agregar nuevas funciones, prácticas, flujos, niveles, preguntas y alternativas.

# 7. Importación desde Excel

Implementa un módulo de importación inicial desde:

`SAMM_spreadsheet.xlsx`

La importación deberá:

1. Leer las hojas relevantes del archivo.
2. Identificar funciones, prácticas, flujos, niveles y preguntas.
3. Importar criterios de calidad.
4. Importar posibles respuestas.
5. Importar ponderaciones.
6. Evitar registros duplicados.
7. Validar campos obligatorios.
8. Mostrar una vista previa antes de confirmar.
9. Mostrar errores por fila.
10. Ejecutarse dentro de una transacción.
11. Permitir revertir la operación cuando falle.
12. Registrar la importación en la bitácora.

Usa `openpyxl` para procesar el archivo Excel.

Agrega un comando CLI similar a:

```bash
flask import-samm --file SAMM_spreadsheet.xlsx
```

También crea una opción de importación desde el panel administrativo.

# 8. Respuestas del cuestionario

Cada respuesta deberá almacenar:

* Assessment.
* Pregunta.
* Usuario respondedor.
* Alternativa seleccionada.
* Valor o ponderación.
* Comentario del respondedor.
* Comentario del revisor.
* Estado.
* Fecha de creación.
* Fecha de última modificación.
* Fecha de envío.
* Fecha de revisión.
* Usuario revisor.
* Indicador de “No aplica”.
* Justificación de “No aplica”.
* Número de versión de la respuesta.

Cuando una pregunta sea respondida, debe conservarse una copia histórica del texto de la pregunta, alternativa y ponderación utilizada. Esto evita que una modificación posterior en el catálogo cambie retroactivamente los assessments anteriores.

# 9. Gestión de evidencias

Cada pregunta podrá tener múltiples archivos de evidencia.

Los archivos deberán almacenar:

* Nombre original.
* Nombre interno seguro.
* Ruta de almacenamiento.
* Tipo MIME.
* Extensión.
* Tamaño.
* Hash SHA-256.
* Usuario que realizó la carga.
* Fecha de carga.
* Descripción de la evidencia.
* Estado de validación.
* Usuario que revisó la evidencia.
* Fecha de revisión.

Implementa las siguientes medidas de seguridad:

* No almacenar archivos directamente dentro de la carpeta pública `static`.
* Generar nombres internos aleatorios mediante UUID.
* Evitar traversal de directorios.
* Usar `secure_filename`.
* Validar extensión y MIME.
* Limitar el tamaño máximo por archivo.
* Limitar la cantidad de archivos por pregunta.
* Rechazar ejecutables y scripts.
* No confiar únicamente en la extensión.
* Calcular hash SHA-256.
* Evitar sobrescritura de archivos.
* Validar permisos antes de descargar.
* Forzar descarga con encabezados seguros.
* Registrar carga, descarga y eliminación en auditoría.
* Permitir configurar extensiones admitidas.
* Dejar preparado un servicio para integración futura con antivirus o ClamAV.

Extensiones iniciales permitidas:

* PDF.
* DOCX.
* XLSX.
* PPTX.
* TXT.
* CSV.
* PNG.
* JPG.
* JPEG.
* ZIP.

Tamaño máximo inicial configurable:

```text
20 MB por archivo
```

# 10. Modelo de datos mínimo

Diseña modelos SQLAlchemy para las siguientes entidades:

* User.
* Role.
* UserRole.
* Organization.
* Assessment.
* AssessmentUser.
* BusinessFunction.
* SecurityPractice.
* PracticeStream.
* MaturityLevel.
* Question.
* QuestionQualityCriterion.
* AnswerSet.
* AnswerOption.
* AssessmentQuestion.
* AssessmentResponse.
* ResponseHistory.
* Evidence.
* Review.
* Recommendation.
* AuditLog.
* ApplicationSetting.
* Notification.

Incluye relaciones, claves foráneas, restricciones, índices y campos de auditoría.

Usa campos como:

* `created_at`
* `updated_at`
* `created_by`
* `updated_by`
* `is_active`

Evita eliminaciones físicas para elementos maestros. Implementa desactivación o soft delete cuando corresponda.

# 11. Cálculo de resultados

El sistema deberá calcular automáticamente:

* Puntaje por pregunta.
* Puntaje por nivel.
* Puntaje por flujo.
* Puntaje por práctica.
* Puntaje por función de negocio.
* Puntaje general del assessment.
* Porcentaje de avance.
* Cantidad de preguntas aprobadas.
* Cantidad de preguntas observadas.
* Cantidad de preguntas pendientes.
* Cantidad de preguntas marcadas como no aplicables.
* Nivel actual.
* Nivel objetivo.
* Brecha entre nivel actual y nivel objetivo.

Las fórmulas deben implementarse en servicios de negocio independientes y contar con pruebas unitarias.

Las preguntas “No aplica” no deberán distorsionar el promedio. El denominador debe considerar únicamente preguntas aplicables.

El sistema deberá permitir configurar si se calcula el resultado usando:

* Respuesta declarada por el usuario.
* Respuesta validada por el revisor.
* Respuesta aprobada final.

# 12. Dashboard administrativo

Crear un dashboard que muestre:

* Total de assessments.
* Assessments activos.
* Assessments completados.
* Organizaciones evaluadas.
* Usuarios activos.
* Porcentaje promedio de avance.
* Resultados promedio por función.
* Preguntas pendientes de revisión.
* Evidencias pendientes de validación.
* Assessments próximos a vencer.
* Actividad reciente.

Incluir gráficos como:

* Radar de madurez por función.
* Barras de madurez por práctica.
* Heatmap de brechas.
* Gráfico de avance.
* Distribución de respuestas.
* Comparación entre nivel actual y objetivo.

# 13. Dashboard del respondedor

Mostrar:

* Assessments asignados.
* Estado de cada assessment.
* Porcentaje de avance.
* Fecha objetivo.
* Preguntas pendientes.
* Preguntas observadas.
* Preguntas rechazadas.
* Preguntas aprobadas.
* Última actividad.
* Acceso rápido para continuar respondiendo.

# 14. Navegación del cuestionario

La pantalla del cuestionario deberá:

* Mostrar un panel lateral con la jerarquía.
* Permitir filtrar por función.
* Permitir filtrar por práctica.
* Permitir filtrar por flujo.
* Permitir filtrar por estado.
* Permitir buscar preguntas por texto.
* Mostrar el avance por sección.
* Indicar visualmente el estado de cada pregunta.
* Permitir guardar automáticamente como borrador.
* Mostrar criterios de calidad.
* Mostrar alternativas y ponderación.
* Mostrar evidencias adjuntas.
* Mostrar observaciones del revisor.
* Tener botones “Anterior” y “Siguiente”.
* Mantener visible el progreso.
* Advertir cuando existan cambios sin guardar.

La interfaz debe funcionar correctamente en escritorio, tablet y dispositivos móviles.

# 15. Administración de preguntas

El administrador deberá contar con una interfaz CRUD que permita:

* Crear preguntas.
* Editar preguntas.
* Duplicar preguntas.
* Activar o desactivar preguntas.
* Ordenar preguntas.
* Asociar criterios de calidad.
* Asociar conjuntos de respuestas.
* Definir ponderaciones.
* Asociar la pregunta a función, práctica, flujo y nivel.
* Consultar dónde se utiliza una pregunta.
* Visualizar historial de cambios.
* Crear nuevas versiones del cuestionario.

No se debe modificar una pregunta histórica que ya forma parte de un assessment iniciado. En ese caso, se deberá crear una nueva versión.

# 16. Versionamiento

Implementa versionamiento del cuestionario.

Cada versión deberá tener:

* Nombre.
* Número de versión.
* Descripción.
* Estado.
* Fecha de publicación.
* Usuario que publicó.
* Preguntas asociadas.

Estados:

* Borrador.
* Publicada.
* Archivada.

Cuando se cree un assessment, deberá quedar vinculado permanentemente a una versión concreta del cuestionario.

# 17. Revisión y aprobación

El flujo de revisión deberá permitir:

1. El respondedor guarda una respuesta.
2. El respondedor adjunta evidencias.
3. El respondedor envía la pregunta a revisión.
4. El revisor analiza respuesta y evidencias.
5. El revisor aprueba, observa o rechaza.
6. Si existe una observación, el usuario corrige y reenvía.
7. Cuando todas las preguntas requeridas estén aprobadas, el assessment puede completarse.

El revisor deberá poder agregar observaciones individuales y generales.

Todas las transiciones deberán quedar registradas en la bitácora.

# 18. Recomendaciones y roadmap

Permite que el administrador o revisor agregue recomendaciones asociadas a:

* Función.
* Práctica.
* Flujo.
* Pregunta.
* Brecha detectada.

Cada recomendación podrá incluir:

* Título.
* Descripción.
* Riesgo asociado.
* Prioridad.
* Esfuerzo.
* Responsable sugerido.
* Plazo.
* Dependencias.
* Estado.
* Indicador de quick win.
* Nivel de madurez objetivo.

Prioridades:

* Crítica.
* Alta.
* Media.
* Baja.

Horizontes sugeridos:

* 0 a 30 días.
* 31 a 90 días.
* 3 a 6 meses.
* 6 a 12 meses.

# 19. Reportes

Genera los siguientes reportes:

* Resumen ejecutivo.
* Resultado general.
* Resultado por función.
* Resultado por práctica.
* Resultado por flujo.
* Nivel actual versus objetivo.
* Matriz de brechas.
* Evidencias por pregunta.
* Preguntas observadas.
* Recomendaciones priorizadas.
* Roadmap de mejora.
* Historial de revisiones.
* Bitácora del assessment.

Formatos requeridos:

* Vista web imprimible.
* Excel.
* PDF.

El reporte PDF debe tener una apariencia corporativa NTT, incluir portada, tabla de contenidos, gráficos, resultados, brechas, recomendaciones y roadmap.

# 20. Diseño visual

El frontend deberá usar Bootstrap 5 y tener un estilo corporativo inspirado en NTT DATA.

La apariencia deberá ser:

* Moderna.
* Elegante.
* Técnica.
* Ejecutiva.
* Minimalista.
* Profesional.
* Responsive.
* Accesible.

Usa una paleta basada en:

```css
--ntt-primary: #0072BC;
--ntt-secondary: #00A7E1;
--ntt-dark: #0B1F33;
--ntt-dark-alt: #132B44;
--ntt-light: #F4F7FA;
--ntt-white: #FFFFFF;
--ntt-success: #198754;
--ntt-warning: #FFC107;
--ntt-danger: #DC3545;
--ntt-muted: #6C757D;
```

Consideraciones visuales:

* Sidebar oscuro.
* Navbar limpia.
* Tarjetas con sombras suaves.
* Bordes moderadamente redondeados.
* Tablas modernas.
* Indicadores de estado con badges.
* Barras de progreso.
* Iconografía Bootstrap Icons.
* Gráficos claros.
* Buen uso del espacio en blanco.
* Tipografía legible.
* Encabezados técnicos.
* Formularios ordenados.
* Modales para operaciones secundarias.
* Toasts para mensajes de éxito y error.
* Tema claro como predeterminado.
* Dejar preparado un tema oscuro opcional.

No copies logotipos ni recursos protegidos desde Internet. Deja una ubicación configurable para incorporar posteriormente el logotipo corporativo autorizado.

# 21. Seguridad de la aplicación

Implementa como mínimo:

* Autenticación segura.
* Hash de contraseñas con Argon2 o bcrypt.
* Control de acceso basado en roles.
* Protección CSRF.
* Validación de entrada.
* Escape de salida.
* Prevención de XSS.
* Prevención de inyección SQL mediante ORM.
* Cookies seguras.
* Cookies `HttpOnly`.
* Cookies `SameSite`.
* Configuración `Secure` en producción.
* Regeneración de sesión al iniciar sesión.
* Cierre de sesión.
* Expiración de sesión.
* Bloqueo temporal después de múltiples intentos fallidos.
* Política de contraseñas.
* Protección de rutas.
* Validación de ownership.
* Encabezados de seguridad.
* Content Security Policy.
* Protección contra clickjacking.
* Protección MIME sniffing.
* Rate limiting.
* Manejo seguro de errores.
* No mostrar stack traces en producción.
* Secretos almacenados en variables de entorno.
* Registro de eventos de seguridad.
* Auditoría de cambios.
* Validación segura de archivos.

Incluye una configuración diferenciada para:

* Desarrollo.
* Pruebas.
* Producción.

# 22. Auditoría

Registra como mínimo:

* Inicio y cierre de sesión.
* Intentos fallidos.
* Creación y modificación de usuarios.
* Cambios de roles.
* Creación y modificación de assessments.
* Cambios de estado.
* Creación y modificación de preguntas.
* Importaciones y exportaciones.
* Respuestas.
* Revisiones.
* Carga de evidencias.
* Descarga de evidencias.
* Eliminación de evidencias.
* Publicación de resultados.
* Generación de reportes.

Cada registro deberá contener:

* Usuario.
* Acción.
* Entidad.
* Identificador de entidad.
* Fecha y hora.
* Dirección IP.
* User-Agent.
* Valores anteriores.
* Valores nuevos.
* Resultado de la operación.

No guardar contraseñas, tokens ni contenido sensible innecesario en los logs.

# 23. API interna

Implementa una API REST versionada bajo:

```text
/api/v1/
```

Endpoints mínimos:

```text
/api/v1/auth/
/api/v1/users/
/api/v1/organizations/
/api/v1/assessments/
/api/v1/questions/
/api/v1/responses/
/api/v1/evidences/
/api/v1/results/
/api/v1/recommendations/
```

La interfaz web podrá usar renderizado del servidor, pero la lógica deberá quedar preparada para integraciones futuras.

Documenta la API con OpenAPI o Swagger.

# 24. Pruebas

Incluye:

* Pruebas unitarias.
* Pruebas de integración.
* Pruebas de autorización.
* Pruebas de autenticación.
* Pruebas de formularios.
* Pruebas de carga de archivos.
* Pruebas de cálculo de puntaje.
* Pruebas de importación Excel.
* Pruebas de transiciones de estado.
* Pruebas de acceso entre organizaciones.
* Pruebas de prevención de IDOR.

Las pruebas deberán ejecutarse con:

```bash
pytest
```

Incluye datos de prueba y fixtures.

# 25. Datos iniciales

Crea un proceso de inicialización que:

1. Cree la base de datos.
2. Ejecute las migraciones.
3. Cree los roles.
4. Cree un administrador inicial.
5. Importe el cuestionario desde Excel.
6. Cree una organización de demostración.
7. Cree un assessment de ejemplo.
8. Cree un usuario respondedor de demostración.

Las credenciales iniciales deberán obtenerse desde variables de entorno y obligar al cambio de contraseña en el primer acceso.

# 26. Configuración

Crea un archivo `.env.example` con variables como:

```env
FLASK_ENV=development
SECRET_KEY=change-me
DATABASE_URL=sqlite:///instance/samm_assessment.db

INITIAL_ADMIN_NAME=Administrador
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=change-me

UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH_MB=20
ALLOWED_EXTENSIONS=pdf,docx,xlsx,pptx,txt,csv,png,jpg,jpeg,zip

SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

ASSESSMENT_AUTOSAVE_SECONDS=30
APP_NAME=NTT DevSecOps Assessment
```

# 27. Despliegue

Entrega instrucciones para ejecutar el sistema en:

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask db upgrade
flask seed
flask run
```

Incluye también los comandos equivalentes para Windows PowerShell.

## Docker

Incluye:

* Dockerfile.
* docker-compose.yml.
* Volumen persistente para SQLite.
* Volumen persistente para evidencias.
* Variables de entorno.
* Healthcheck.
* Usuario no root.

## Producción Linux

Documenta:

* Gunicorn.
* Nginx.
* systemd.
* Permisos de carpetas.
* Certificado TLS.
* Respaldo de la base de datos.
* Respaldo de evidencias.
* Rotación de logs.

# 28. Respaldo y restauración

Implementa comandos para:

```bash
flask backup
flask restore --file backup.zip
```

El respaldo deberá contener:

* Base de datos SQLite.
* Evidencias.
* Archivo de metadatos.
* Fecha.
* Versión de la aplicación.
* Hashes de integridad.

La restauración deberá validar integridad antes de reemplazar información.

# 29. README

El archivo README deberá explicar:

* Objetivo del proyecto.
* Arquitectura.
* Requisitos.
* Instalación.
* Configuración.
* Migraciones.
* Importación del Excel.
* Creación del administrador.
* Ejecución.
* Pruebas.
* Docker.
* Despliegue.
* Respaldos.
* Seguridad.
* Estructura de carpetas.
* Credenciales de demostración.
* Limitaciones conocidas.
* Evolución futura hacia PostgreSQL.

# 30. Criterios de aceptación

La solución se considerará completa cuando:

1. Un administrador pueda iniciar sesión.
2. El administrador pueda importar el cuestionario desde Excel.
3. Las preguntas queden organizadas jerárquicamente.
4. El administrador pueda editar y versionar preguntas.
5. El administrador pueda crear una organización.
6. El administrador pueda crear un assessment.
7. El administrador pueda asignar usuarios.
8. Un respondedor pueda ingresar y ver solamente sus assessments.
9. El respondedor pueda contestar preguntas.
10. El respondedor pueda guardar borradores.
11. El respondedor pueda adjuntar evidencias.
12. El respondedor pueda enviar respuestas a revisión.
13. Un revisor pueda aprobar, observar o rechazar.
14. El sistema pueda calcular resultados automáticamente.
15. El dashboard pueda mostrar avance, puntajes y brechas.
16. El sistema pueda generar reportes.
17. La aplicación aplique RBAC correctamente.
18. Los archivos no sean accesibles sin autorización.
19. Las acciones relevantes queden auditadas.
20. Las pruebas automatizadas principales sean exitosas.

# 31. Forma de entrega solicitada

Desarrolla la solución de manera incremental y entrega el resultado en el siguiente orden:

## Fase 1: Diseño

* Resumen de arquitectura.
* Modelo de datos.
* Diagrama de entidades.
* Flujos funcionales.
* Decisiones técnicas.
* Riesgos y supuestos.

## Fase 2: Proyecto base

* Estructura de directorios.
* Configuración.
* Modelos.
* Migraciones.
* Autenticación.
* Roles.
* Layout Bootstrap 5.

## Fase 3: Catálogo SAMM

* Importación Excel.
* Administración de funciones.
* Administración de prácticas.
* Administración de flujos.
* Administración de niveles.
* Administración de preguntas.
* Versionamiento.

## Fase 4: Assessment

* Organizaciones.
* Creación de assessments.
* Asignación de usuarios.
* Cuestionario.
* Respuestas.
* Evidencias.
* Flujo de revisión.

## Fase 5: Resultados

* Cálculos.
* Dashboard.
* Gráficos.
* Brechas.
* Recomendaciones.
* Roadmap.

## Fase 6: Reportes y despliegue

* Exportación Excel.
* Reporte PDF.
* Docker.
* Nginx.
* Gunicorn.
* systemd.
* Documentación.

En cada fase entrega archivos completos, no solamente fragmentos aislados.

Cuando modifiques un archivo previamente generado, entrega nuevamente el archivo completo y señala claramente su ruta.

No uses pseudocódigo para las funciones principales.

No omitas código usando frases como:

* “Aquí iría la lógica”.
* “Completar posteriormente”.
* “Resto del código”.
* “Implementar según necesidad”.

Incluye manejo de errores, validaciones, mensajes para el usuario y comentarios técnicos donde sean relevantes.

Antes de generar el código, presenta primero:

1. La arquitectura propuesta.
2. El modelo entidad-relación.
3. La estructura completa del proyecto.
4. Las principales decisiones de diseño.
5. Los supuestos adoptados.

Luego comienza la implementación de la Fase 1.
