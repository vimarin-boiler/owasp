# Checklist de seguridad de producción

## Identidad y secretos

- [ ] `SECRET_KEY` tiene alta entropía y no usa el valor de ejemplo.
- [ ] Contraseñas iniciales fueron cambiadas.
- [ ] `CREATE_DEMO_DATA=false`.
- [ ] `.env` no está en Git y tiene modo `0640` o más restrictivo.
- [ ] Se revisaron administradores y revisores activos.

## Transporte y sesión

- [ ] TLS 1.2/1.3 válido y cadena completa.
- [ ] HTTP redirige a HTTPS.
- [ ] `SESSION_COOKIE_SECURE=true`.
- [ ] `FORCE_HTTPS=true`.
- [ ] `TRUSTED_HOSTS` contiene solo FQDN autorizados.
- [ ] HSTS se habilitó después de verificar HTTPS.

## Red y reverse proxy

- [ ] Gunicorn escucha solo en loopback o red interna.
- [ ] Firewall permite únicamente 443 y administración autorizada.
- [ ] Nginx limita tamaño de request de acuerdo con evidencias permitidas.
- [ ] Proxy headers solo se confían desde Nginx.

## Sistema operativo

- [ ] Servicio usa usuario sin login y sin privilegios.
- [ ] systemd tiene `NoNewPrivileges`, `ProtectSystem` y rutas de escritura limitadas.
- [ ] Parches de seguridad del SO y Python están al día.
- [ ] Nginx y Docker no se ejecutan con privilegios innecesarios.

## Base y evidencias

- [ ] Base, evidencias y backups están en carpetas no públicas.
- [ ] Permisos de carpetas son `0750` o más restrictivos.
- [ ] Se integró antivirus real antes de aceptar archivos externos.
- [ ] Se definió cuota de almacenamiento y monitoreo de disco.
- [ ] Backups se cifran y copian fuera del host.
- [ ] Se probó una restauración reciente.

## Aplicación

- [ ] `flask check-config` finaliza correctamente.
- [ ] Migraciones están aplicadas.
- [ ] `pytest` y smoke tests pasan en CI.
- [ ] Rate limiting usa almacenamiento compartido si hay múltiples procesos/instancias.
- [ ] Chart.js se sirve localmente o desde una fuente aprobada.
- [ ] CSP fue revisada para integraciones adicionales.
- [ ] Logs no contienen secretos ni evidencia sensible.

## Operación

- [ ] Healthcheck está monitoreado.
- [ ] Hay alertas de capacidad, errores 5xx e intentos fallidos.
- [ ] Logrotate está activo.
- [ ] Timer de backup está activo.
- [ ] Se documentó RPO, RTO y responsables.
- [ ] Existe procedimiento de respuesta a incidentes.
