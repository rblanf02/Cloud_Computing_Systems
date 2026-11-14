# CloudFile Exchange

Sistema de intercambio de ficheros (documentos y fotos) entre aplicaciones
(PC, tablet, movil) y la nube, con autenticacion, autorizacion (read/write/update),
control de versiones, integridad SHA-256, comparticion y LogBook (registro de accesos
y operaciones).

Proyecto de la asignatura **Cloud Computing Systems**.

## Stack

| Capa | Tecnologia |
|---|---|
| Cloud | Azure (Blob Storage + versioning, Container Apps, PostgreSQL Flexible Server) |
| Backend | Python + FastAPI + SQLAlchemy + JWT |
| Frontend | React + Vite (navegador PC/tablet/movil) |
| Base de datos | PostgreSQL |
| Storage local | Azurite (emulador de Azure Blob) |
| Contenedores | Docker + docker-compose |
| CI/CD | GitHub Actions |

## Funcionalidad

- Registro/login con JWT y sesiones revocables por inactividad.
- Cada usuario nuevo recibe permisos `can_read`, `can_write` y `can_update`.
- Admin puede listar usuarios y revocar o devolver permisos desde la UI.
- Subida de ficheros, versionado explicito, historial, descarga y restauracion.
- SHA-256 por version: se muestra en la UI y se verifica en cada descarga.
- Comparticion por usuario con niveles `reader`, `editor` y `manager`.
- Papelera con restauracion y borrado definitivo.
- LogBook filtrado por usuario (el admin ve todo) con export CSV/JSON.
- HTTPS local con certificado de confianza (mkcert).

## Inicio rapido

```powershell
Copy-Item .env.example .env
powershell -ExecutionPolicy Bypass -File infra/nginx/gen-cert.ps1 -Ip <IP_LAN>
docker compose up -d --build
```

Abrir `https://localhost:8443`. La API y Swagger estan en
`https://localhost:8443/docs`. El backend no publica el puerto `8000`; `5432`
(PostgreSQL) y `10000` (Azurite) quedan accesibles para herramientas locales.

## HTTPS local

`gen-cert.ps1` usa **mkcert** si esta instalado (recomendado: `winget install
FiloSottile.mkcert`). El certificado cubre `localhost`, `127.0.0.1` y la IP de la LAN
que se pase con `-Ip`.

- El CA local se instala en el almacen de confianza de Windows la primera vez.
- Para tablet/movil hay que instalar `infra/nginx/certs/rootCA.pem` como CA de confianza
  en el dispositivo.
- `curl.exe` en Windows puede fallar por la comprobacion de revocacion de Schannel;
  usar `curl.exe --ssl-no-revoke https://localhost:8443/health`.

## Tests

```powershell
docker compose up -d db azurite
docker compose run --rm backend pytest -q
cd frontend
npm ci
npm run build
```

## Contenido del repositorio

```
backend/           FastAPI, modelos, routers y tests
frontend/          React + Vite, nginx y Dockerfile
infra/nginx/       Proxy TLS y script de certificados
docs/              Documentacion del proyecto
docker-compose.yml Entorno local (backend, frontend, Postgres, Azurite y nginx)
.env.example       Variables de entorno de ejemplo
```

## Documentos

| Fichero | Contenido |
|---|---|
| `docs/PROYECTO_COMPLETO.md` | **Documento maestro**: todo el proyecto explicado |
| `docs/00_plan.md` | Plan completo, decisiones y fases |
| `docs/01_problem_statement.md` | Seccion 1 de la presentacion |
| `docs/02_state_of_the_art.md` | Seccion 2 + comparativa de soluciones |
| `docs/03_specifications.md` | Seccion 3 (objetivos, tech, riesgos, exito) |
| `docs/04_architecture.md` | Diagrama, modelo de datos y API |
| `docs/05_division_of_work.md` | Reparto entre Jose, Ruben, Maria, Diego y Nico |
| `docs/06_backend_explicado.md` | El backend explicado en lenguaje llano |
| `docs/07_historial_de_cambios.md` | Registro de cambios y autoria |
| `docs/presentation_outline.md` | Guion de slides |
