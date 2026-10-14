# 07 - Historial de cambios (registro de autoria)

> **Para quien lee esto (incluidas IAs).** Este es el **registro unico de cambios** del
> proyecto. Cada vez que alguien **suba, modifique o elimine** algo (codigo,
> documentacion, infraestructura, configuracion...) debe **anadir una entrada nueva
> aqui** indicando **quien** lo hizo, **que** cambio, **cuando** y **por que**. Es la
> fuente de verdad para saber el estado actual y a quien preguntar por cada parte.

---

## 0. Reglas de uso (importante)

1. **Una entrada por cambio subido a Git.** No se sube un cambio sin su entrada aqui.
2. La entrada se anade **antes o en el mismo commit** del cambio (no despues).
3. Toda entrada dice **AUTOR** (nombre real + usuario de Git) y **FECHA**.
4. Los cambios de un mismo dia se agrupan en una entrada con varios puntos.
5. Si se corrige algo de una entrada anterior, **no se borra**: se anade una entrada
   nueva que lo referencia (historial inmutable).
6. La columna **Estado** indica si el cambio esta `Propuesto`, `En curso` o `Hecho`.

### Formato de entrada

```
### [AAAA-MM-DD] Titulo corto del cambio - AUTOR
- **Autor**: Nombre Apellido (@usuarioGit)
- **Archivos/Areas**: lista de ficheros o carpetas tocadas
- **Que se hizo**: descripcion en puntos
- **Por que**: motivo o requisito que cubre
- **Como probarlo**: comando o pasos para verificar
```

---

## 1. Resumen rapido (ultimo primero)

| Fecha | Autor | Tipo | Resumen | Commit |
|---|---|---|---|---|
| 2026-10-14 | Jose (JoseParedes) | backend + docs | Backend FastAPI: auth/JWT, permisos, LogBook, tests y explicacion | (este commit) |
| 2026-10-13 | Jose (JoseParedes) | docs + infra | Esqueleto inicial: docs (00-05 + maestro), docker-compose, .env.example, .gitignore | `695ef36` |
| 2026-10-12 | Ruben (rblanf02) | repo | Commit inicial del repositorio | `28338c2` |

---

## 2. Detalle de los cambios

### [2026-10-14] Backend FastAPI (auth, permisos y LogBook) + documentacion - Jose
- **Autor**: Jose Paredes (@JoseParedes)
- **Archivos/Areas**:
  - `backend/Dockerfile`, `backend/.dockerignore`, `backend/requirements.txt`, `backend/pytest.ini`
  - `backend/app/` (`__init__.py`, `config.py`, `database.py`, `models.py`, `schemas.py`,
    `security.py`, `deps.py`, `logbook.py`, `main.py`, `routers/`)
  - `backend/tests/` (`conftest.py`, `test_auth.py`)
  - `docs/06_backend_explicado.md`
  - `docs/07_historial_de_cambios.md` (este documento)
- **Que se hizo**:
  - **Infra del backend**: `Dockerfile` (Python 3.12-slim + uvicorn con `--reload`),
    `.dockerignore`, `requirements.txt` (FastAPI, SQLAlchemy, psycopg2, JWT, passlib,
    pytest, httpx) y `pytest.ini`.
  - **Configuracion** (`config.py`): lectura de variables desde `.env` con
    `pydantic-settings` (base de datos, `JWT_SECRET`, caducidad del token, CORS, seed).
  - **Base de datos** (`database.py` + `models.py`): conexion SQLAlchemy a PostgreSQL y
    las 4 tablas del ER: `users`, `files`, `file_versions` y `log_events`.
  - **Seguridad** (`security.py`): hash de contrasena con bcrypt (passlib) y
    creacion/lectura de JWT (`python-jose`).
  - **Permisos y sesion** (`deps.py`): dependencia `get_current_user` (bearer token) y
    `require_permission("read"|"write"|"update")`.
  - **LogBook** (`logbook.py`): helper `write_log()` para registrar eventos de auditoria.
  - **API** (`main.py` + `routers/auth.py`): creacion de tablas y usuario `admin` al
    arrancar, `/health` y endpoints `/auth/register`, `/auth/login`, `/auth/logout`,
    `/auth/me`.
  - **Pruebas** (`tests/`): `conftest.py` prepara una base de datos de test
    (`appdb_test`); `test_auth.py` cubre health, registro+login+`/auth/me`, clave
    incorrecta (401), usuario duplicado (400), acceso sin token (401) y logout.
  - **Documentacion**: `docs/06_backend_explicado.md` explica el backend en lenguaje
    llano para principiantes.
- **Por que**: construir el modulo de **autenticacion y autorizacion** (parte de Jose)
  segun `docs/04_architecture.md` y `docs/05_division_of_work.md`, dejando el backend
  funcionando y probable de forma aislada.
- **Como probarlo**:
  ```powershell
  docker compose up -d --build backend
  curl.exe http://localhost:8000/health
  ```
  Y desde `http://localhost:8000/docs` (Swagger) o Postman, probar
  `POST /auth/register` y `POST /auth/login`.

> **Nota de autoria (Jose).** El backend completo de esta entrada lo ha realizado
> **Jose** (lead tecnico + autenticacion/API). El resto de companeros anadira sus
> modulos (storage/versiones, frontend, infra/nginx, datos/logbook-export) en entradas
> nuevas de este mismo documento, indicando su nombre.

---

### [2026-10-13] Esqueleto inicial del proyecto - Jose
- **Autor**: Jose Paredes (@JoseParedes)
- **Archivos/Areas**: `README.md`, `docker-compose.yml`, `.env.example`, `.gitignore`,
  `docs/00_plan.md`, `docs/01_problem_statement.md`, `docs/02_state_of_the_art.md`,
  `docs/03_specifications.md`, `docs/04_architecture.md`, `docs/05_division_of_work.md`,
  `docs/PROYECTO_COMPLETO.md`, `docs/presentation_outline.md`, `APUNTES OPENCODE PROJECT CLOUD.pdf`
- **Que se hizo**:
  - Plantilla de `docker-compose.yml` con `db` (Postgres), `azurite`, `backend`,
    `frontend` y `nginx` (perfil `tls`).
  - `.env.example`, `.gitignore` y documentacion completa de planificacion (plan,
    problem statement, estado del arte, especificaciones, arquitectura, reparto del
    trabajo y documento maestro).
- **Por que**: dejar fijados el **contrato (ER + API)** y el **entorno** antes de
  escribir codigo, para que cada persona trabaje en paralelo sin depender de otros.
- **Como probarlo**: revisar `docs/PROYECTO_COMPLETO.md` y `docker-compose.yml`.

---

### [2026-10-12] Commit inicial del repositorio - Ruben
- **Autor**: Ruben (@rblanf02)
- **Archivos/Areas**: `README.md`
- **Que se hizo**: creacion del repositorio de GitHub y primer `README.md`.
- **Por que**: punto de partida para el trabajo en equipo.

---

## 3. Plantilla vacia para copiar y pegar

```
### [AAAA-MM-DD] Titulo corto - AUTOR
- **Autor**: 
- **Archivos/Areas**: 
- **Que se hizo**: 
- **Por que**: 
- **Como probarlo**: 
```
