# 03 - Especificaciones y requisitos

## 3.1 Objetivos (metas y limites precisos)

Objetivos:
- App accesible desde PC, tablet y movil via navegador (HTTPS).
- Login/logout con autenticacion segura (hash + JWT).
- Autorizacion por derechos **read / write / update**.
- Subir, descargar y listar ficheros almacenados en Azure Blob Storage.
- **Control de versiones**: fecha, tamano y numero de version por fichero.
- **LogBook**: registro de logins y operaciones, exportable a CSV/JSON.

Limites (fuera de alcance en la 1a version):
- Edicion colaborativa en tiempo real.
- Apps nativas iOS/Android (se usa web responsive).
- Sincronizacion automatica de carpetas de escritorio.

## 3.2 Fuentes (informacion adicional / contactos)

- Documentacion oficial de Azure (Blob, Entra ID, Container Apps).
- Documentacion de FastAPI, SQLAlchemy, Streamlit.
- OWASP (seguridad), RFC 7519 (JWT), RFC 8446 (TLS).
- Profesor de la asignatura (rúbrica y requisitos de la presentacion).

## 3.3 Herramientas y tecnologias (con justificacion)

| Ambito | Tecnologia | Justificacion |
|---|---|---|
| Cloud | Azure | Credito for Students; Blob versioning; Entra ID; SDK Python. |
| Backend | FastAPI | Rapido, Python (perfil del equipo), Swagger automatico. |
| Auth | JWT + bcrypt | Estandar, sencillo, control de roles. |
| BD | PostgreSQL | Relacional, ideal para versiones y auditoria. |
| Storage | Azure Blob + Azurite local | Versionado + emulacion local sin coste. |
| Frontend | Streamlit | Un lenguaje, sin frontend dedicado, multi-dispositivo. |
| Contenedores | Docker + Compose | Requisito del profesor; entorno reproducible. |
| CI/CD | GitHub Actions | Automatizacion de tests. |

## 3.4 Riesgos

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Fuga de credenciales / secrets | Alto | `.env` fuera del repo; Key Vault en Azure; rotacion. |
| Sobrecoste cloud | Medio | Azure for Students; Azurite local; apagar recursos. |
| Curva de aprendizaje (Docker/Azure) | Medio | Local primero; usar plantillas; IA como apoyo. |
| Errores de configuracion TLS/CORS | Medio | Checklist; probar HTTPS en local; docs. |
| Perdida de datos | Alto | Backups/versionado; pruebas. |
| Scope creep | Medio | Limites definidos en 3.1. |

## 3.5 Medidas de exito (criterios verificables)

- [ ] Las 6 capacidades funcionan: login, logout, upload, download, list, logbook.
- [ ] Autenticacion y autorizacion read/write/update verificadas con tests.
- [ ] Control de versiones: subir 3 veces un fichero genera 3 versiones con fecha/tamano.
- [ ] LogBook exportable a CSV y JSON con logins y operaciones.
- [ ] Transferencia por HTTPS (certificado valido en cloud).
- [ ] Despliegue funcional en Azure + demo en vivo.
- [ ] Coste dentro del credito.
