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
| 2026-11-03 | Jose (JoseParedes) | backend + docs + tests | P2: permisos de 3 niveles, versionado explícito, historial/restore y admin | (pendiente) |
| 2026-11-03 | Jose (JoseParedes) | backend + config | P1: storage Azure/Azurite, versionado, upload/list/download y tests | (pendiente) |
| 2026-11-03 | Jose (JoseParedes) | backend + config | P0: seguridad de auth, CORS, JWT simplificado y secretos por entorno | (pendiente) |
| 2026-10-14 | Jose (JoseParedes) | backend + docs | Backend FastAPI: auth/JWT, permisos, LogBook, tests y explicacion | (este commit) |
| 2026-10-13 | Jose (JoseParedes) | docs + infra | Esqueleto inicial: docs (00-05 + maestro), docker-compose, .env.example, .gitignore | `695ef36` |
| 2026-10-12 | Ruben (rblanf02) | repo | Commit inicial del repositorio | `28338c2` |

---

## 2. Detalle de los cambios

### [2026-11-03] P2: permisos de 3 niveles, versionado explícito y admin - Jose
- **Autor**: Jose Paredes (@JoseParedes)
- **Archivos/Areas**:
  - `backend/app/routers/files.py`
  - `backend/app/routers/admin.py` (nuevo)
  - `backend/app/deps.py`
  - `backend/app/models.py`
  - `backend/app/schemas.py`
  - `backend/app/main.py`
  - `backend/tests/test_files.py`
  - `backend/tests/test_admin.py` (nuevo)
  - `docs/04_architecture.md`, `docs/06_backend_explicado.md`
- **Que se hizo**:
  - Se fijo el modelo final: cada usuario tiene `can_read`, `can_write` y `can_update`;
    no hay sharing entre usuarios ni tabla `file_shares`. El admin conserva bypass total.
  - `POST /files/upload` solo crea ficheros nuevos; si el nombre ya existe para ese
    usuario responde `409` y remite a `POST /files/{id}/versions`.
  - Se anadieron `POST /files/{id}/versions`, `GET /files/{id}/versions`,
    `GET /files/{id}/versions/{v}/download` y `POST /files/{id}/versions/{v}/restore`.
  - Restaurar crea una version nueva; no mueve el puntero hacia atras ni borra historial.
  - `FileVersion` guarda `content_type` para conservar el MIME de cada version.
  - Se anadieron `GET /admin/users`, `PATCH /admin/users/{id}/permissions` y
    `GET /admin/files`; el patch solo acepta los tres permisos.
  - Se anadieron tests de creacion, versionado, permisos, historial, restore, admin y
    revocacion de permisos.
- **Por que**: el producto es un area personal con administracion global, no un sistema
  de comparticion; separar crear de versionar evita versiones accidentales y permite
  recuperar contenido antiguo sin perder trazabilidad.
- **Como probarlo**:
  ```powershell
  docker compose down -v
  docker compose up -d --build backend
  docker compose exec backend pytest
  ```
  El `down -v` es necesario en local porque `FileVersion.content_type` cambia el esquema
  y el proyecto no usa migraciones automaticas.

---

### [2026-11-03] P1: storage, versionado y endpoints de ficheros - Jose
- **Autor**: Jose Paredes (@JoseParedes)
- **Archivos/Areas**:
  - `backend/app/storage.py`
  - `backend/app/routers/files.py`
  - `backend/app/models.py`
  - `backend/app/schemas.py`
  - `backend/app/config.py`
  - `backend/app/deps.py`
  - `backend/app/logbook.py`
  - `backend/app/routers/auth.py`
  - `backend/app/main.py`
  - `backend/requirements.txt`
  - `backend/tests/conftest.py`
  - `backend/tests/test_files.py`
  - `.env` (local, no versionado) y `.env.example`
- **Que se hizo**:
  - Se añadio una capa de storage con `AzureBlobStorage` (Azurite/Azure) e
    `InMemoryStorage` para tests, seleccionable mediante `get_storage()`.
  - Se añadieron las constraints que impiden duplicar `(owner_id, filename)` y
    `(file_id, version_number)`, mas indices para las consultas del LogBook.
  - Se implementaron `POST /files/upload`, `GET /files` y
    `GET /files/{id}/download` con permisos `write`/`read`, validacion de tamano y
    aislamiento por propietario (los ficheros ajenos responden `404`).
  - Cada subida del mismo nombre crea una version nueva (`owner/{file_id}/v{n}`);
    se registra `UPLOAD`, `LIST` y `DOWNLOAD` en el LogBook.
  - `write_log()` ya no hace `commit()`; ahora la transaccion la cierra el endpoint,
    de modo que el evento de auditoria y el cambio de negocio se guardan juntos.
  - Se añadieron tests de versionado, permisos, aislamiento entre usuarios, saneado
    de nombres, limite de tamano y rollback si falla el storage.
- **Por que**: cubrir la parte de almacenamiento y versionado del MVP local,
  manteniendo la auditoria atomica y el mismo contrato de API documentado.
- **Como probarlo**:
  ```powershell
  docker compose up -d --build backend
  docker compose exec backend pytest
  ```
  Y subir dos veces el mismo fichero para comprobar que `current_version` pasa a `2`.

---

### [2026-11-03] P0: seguridad de autenticacion y configuracion - Jose
- **Autor**: Jose Paredes (@JoseParedes)
- **Archivos/Areas**:
  - `backend/app/config.py`
  - `backend/app/main.py`
  - `backend/app/schemas.py`
  - `backend/app/routers/auth.py`
  - `backend/tests/test_auth.py`
  - `.env.example`
  - `.env` (local, no versionado)
  - `docs/06_backend_explicado.md`
  - `docs/PROYECTO_COMPLETO.md`
  - `docs/07_historial_de_cambios.md`
- **Que se hizo**:
  - Se eliminaron `is_admin`, `can_write` y `can_update` de `UserRegister`; el registro
    publico crea usuarios con `can_read=True` y sin permisos de escritura/actualizacion.
  - Se activo `extra="forbid"` para rechazar intentos de enviar privilegios en el JSON.
  - Se simplifico el JWT para que solo transporte `sub` (identidad) y la caducidad; los
    permisos se leen siempre de la base de datos.
  - Se configuro CORS con origenes explicitos y sin credenciales, ya que el frontend
    JavaScript usara `Authorization: Bearer`.
  - Se movieron el secreto JWT, el usuario/email y la contrasena del admin a variables
    de entorno (`JWT_SECRET`, `SEED_ADMIN_*`).
  - Se genero un `.env` local real con secretos aleatorios (no versionado).
  - Se añadieron tests para comprobar los permisos por defecto, rechazar privilegios
    enviados en el registro y verificar que `HTTPBearer` rechaza tokens invalidos y
    esquemas de autorizacion distintos de `Bearer`.
- **Por que**: cerrar la escalada de privilegios del registro publico y dejar la
  configuracion sensible fuera del codigo antes de implementar los endpoints de ficheros.
- **Como probarlo**:
  ```powershell
  docker compose exec backend pytest
  ```
  Y comprobar que `POST /auth/register` con `is_admin` responde `422`.

---

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
