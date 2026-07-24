# Seguridad de evidencias

## Flujo de carga

1. Flask limita el tamaño total del request.
2. `EvidenceService` valida nombre y extensión.
3. El stream se copia a un archivo exclusivo dentro de `.quarantine`.
4. Se calcula SHA-256 durante la escritura.
5. Se aplica el límite individual por archivo.
6. Se inspecciona la firma binaria.
7. Los formatos Office y ZIP se abren sin extraer.
8. Se rechazan rutas absolutas, traversal, symlinks, ejecutables y scripts.
9. Se limita cantidad, tamaño descomprimido y relación de compresión.
10. Se invoca el contrato de scanner antivirus.
11. Se evita un hash duplicado para la misma pregunta.
12. Se mueve atómicamente al destino privado con UUID.
13. Se persisten metadatos y auditoría.

## Layout de almacenamiento

```text
uploads/
├── .quarantine/
└── {assessment_uuid}/
    └── {assessment_question_uuid}/
        └── {random_uuid}.{extension}
```

Los nombres y rutas recibidos desde el navegador nunca se utilizan como ruta de destino.

## Validación por formato

- PDF: cabecera `%PDF-`.
- PNG: firma PNG.
- JPG/JPEG: firma JPEG.
- TXT/CSV: UTF-8 y ausencia de bytes NUL.
- DOCX: contenedor ZIP y entrada `word/`.
- XLSX: contenedor ZIP y entrada `xl/`.
- PPTX: contenedor ZIP y entrada `ppt/`.
- ZIP: estructura válida y contenido inspeccionado.

## Archivos comprimidos

Se rechaza:

- Más de 5.000 entradas.
- Más de 500 MB descomprimidos.
- Relación de compresión superior a 100:1.
- Entradas con tamaño positivo y cero bytes comprimidos.
- Rutas absolutas o componentes `..`.
- Enlaces simbólicos.
- Extensiones ejecutables o de script.

## Descarga

Antes de entregar un archivo se valida:

- Evidencia activa.
- Existencia física.
- Assessment visible para el usuario.
- Asignación o rol administrativo.

La respuesta usa:

```text
Content-Disposition: attachment
Content-Type: application/octet-stream
Cache-Control: no-store, private
X-Content-Type-Options: nosniff
Content-Security-Policy: sandbox
```

## Antivirus

`AntivirusScanner` define el contrato. `NullAntivirusScanner` permite desarrollo local, pero no brinda detección de malware. La integración recomendada para producción es ClamAV mediante socket local o un servicio de análisis aislado.

## Auditoría

Se registran:

- Carga.
- Descarga.
- Eliminación.
- Validación o rechazo.
- Hash, tamaño, tipo detectado y resultado del scanner.

Nunca se registra el contenido binario del archivo.
