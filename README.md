# CloudFile Exchange

Sistema de intercambio de ficheros (documentos y fotos) entre aplicaciones
(PC, tablet, movil) y la nube, con autenticacion, autorizacion (read/write/update),
control de versiones y LogBook (registro de accesos y operaciones).

Proyecto de la asignatura **Cloud Computing Systems**.

## Stack

| Capa | Tecnologia |
|---|---|
| Cloud | Azure (Blob Storage + versioning, Container Apps, PostgreSQL Flexible Server) |
| Backend | Python + FastAPI + SQLAlchemy + JWT |
| Frontend | Streamlit (navegador PC/tablet/movil) |
| Base de datos | PostgreSQL |
| Storage local | Azurite (emulador de Azure Blob) |
| Contenedores | Docker + docker-compose |
| CI/CD | GitHub Actions |

## Contenido del repositorio

```
docs/              Documentacion: plan, presentacion (secciones 1-3),
                   arquitectura, reparto del trabajo y guion de slides.
docker-compose.yml Plantilla del entorno local (backend, frontend, Postgres,
                   Azurite y nginx con TLS opcional).
.env.example       Variables de entorno de ejemplo.
```

> El `docker-compose.yml` es la plantilla del entorno. Referencia carpetas
> `backend/` y `frontend/` que todavia no existen: se crearan durante la
> implementacion (ver `docs/05_division_of_work.md`).

## Documentos

| Fichero | Contenido |
|---|---|
| `docs/PROYECTO_COMPLETO.md` | **Documento maestro**: todo el proyecto explicado y listo para enviar a una IA |
| `docs/00_plan.md` | Plan completo, decisiones y fases |
| `docs/01_problem_statement.md` | Seccion 1 de la presentacion |
| `docs/02_state_of_the_art.md` | Seccion 2 + comparativa de soluciones |
| `docs/03_specifications.md` | Seccion 3 (objetivos, tech, riesgos, exito) |
| `docs/04_architecture.md` | Diagrama, modelo de datos y API |
| `docs/05_division_of_work.md` | Reparto entre Jose, Ruben, Maria, Diego y Nico |
| `docs/presentation_outline.md` | Guion de slides |
