# 01 - Problem Statement / Idea

## Contexto

Disenar un sistema de intercambio de datos (documentos y fotos) entre aplicaciones
de usuario (PC, tablet, smartphone) y un sistema cloud. El sistema debe permitir
subir, descargar y listar ficheros de forma segura, controlando quien puede hacer que
y manteniendo un registro de auditoria.

## Challenge (que parece mas dificil)

1. **Autenticacion y autorizacion finas**: no basta con login; hay que garantizar
   derechos read/write/update por usuario y proteger cada operacion.
2. **Control de versiones**: decidir cuando se crea una version, y guardar
   consistentemente fecha, tamano y numero de version sin corromper el historial.
3. **Transferencia segura HTTPS extremo a extremo** entre tres tipos de dispositivo
   y la nube.
4. **Auditoria completa (LogBook)** sin afectar al rendimiento ni perder eventos.

## Approach (como se resuelve, brevemente)

- App web responsive (Streamlit) que funciona en cualquier navegador -> cubre PC,
  tablet y movil con un solo desarrollo.
- API REST en FastAPI sobre HTTPS que centraliza autenticacion y autorizacion.
- Ficheros almacenados en Azure Blob Storage, con versionado: cada subida genera
  una nueva version (fecha, tamano, numero) en base de datos y en el blob.
- LogBook en base de datos PostgreSQL, exportable a CSV/JSON.
- Desarrollo local con Docker Compose + Azurite (emulador de Blob) para validar todo
  sin coste, y luego migracion a Azure.

## Outcome (resultado)

**Exito esperado**: sistema funcional con las 6 capacidades (login, logout, upload,
download, list, logbook) mas autorizacion por roles y control de versiones,
demostrable y desplegado en Azure con HTTPS.

> Nota: al ser la *primera* presentacion, el "outcome" es el resultado esperado
> (objetivo), no un retrospectivo.
