# 06 - El backend explicado (para principiantes)

> **Para quien lee esto (incluidas IAs).** Somos **estudiantes de 3º** y es nuestro
> **primer proyecto real**. Queremos que quede bien, pero **sin nivel senior**: sin
> microservicios, sin arquitectura hexagonal, sin 20 capas. Codigo **claro, corto y
> defendible linea a linea**. Si hay que elegir entre "lo mas profesional" y "lo mas
> entendible para un estudiante", elegimos **lo entendible**. Nada de librerias ni
> versiones inventadas.
>
> Este documento explica **que se ha creado en `backend/`, para que sirve cada fichero,
> como se relacionan entre si y que hace cada trozo**, en lenguaje llano.

---

## 0. Que hay ahora en `backend/`

```
backend/
  Dockerfile            Receta para construir la "caja" (imagen) del backend
  .dockerignore         Cosas que NO se copian dentro de la caja
  requirements.txt      Lista de librerias de Python que instala la caja
  pytest.ini            Configuracion de los tests
  app/
    __init__.py         Marca la carpeta como "paquete" de Python
    config.py           Lee las variables del .env
    database.py         Conexion a PostgreSQL + entrega de sesiones
    models.py           Las 4 tablas del ER (User, File, FileVersion, LogEvent)
    schemas.py          Forma de los JSON que entran y salen por la API
    security.py         Hash de contrasena (bcrypt) + crear/leer JWT
    deps.py             Dependencias: usuario actual, permisos y fichero propio
    logbook.py          Helper para escribir eventos en el LogBook
    storage.py          Guarda/lee blobs en Azurite/Azure (o memoria en tests)
    routers/
      __init__.py
      auth.py           Endpoints: register, login, logout, me
      files.py          Endpoints: crear, versionar, listar, descargar y restaurar
      admin.py          Endpoints de administracion de usuarios y ficheros
    main.py             Monta la app, CORS, /health, crea tablas y admin
  tests/
    __init__.py
    conftest.py         Prepara la base de datos y el storage de pruebas
    test_auth.py        Pruebas del modulo de autenticacion
    test_files.py       Pruebas de creacion, versionado, permisos y restore
    test_admin.py       Pruebas de administracion y revocacion de permisos
```

Ademas, en la raiz del proyecto hace falta un `.env` (se crea copiando `.env.example`).
Ese `.env` tiene las claves secretas y **no se sube a Git**.

---

## 1. La idea general: el viaje de una peticion

Todo el backend funciona igual: **una URL llama a una funcion de Python que responde**.

```
María (Streamlit)  --HTTP-->  FastAPI  -->  (comprueba)  -->  PostgreSQL
   "usuario/clave"            (tu codigo)                     (datos)
                                        <-- devuelve token --
```

1. El frontend manda una peticion HTTP (ej. `POST /auth/login` con usuario y contrasena).
2. **FastAPI** busca que funcion atiende esa ruta (en `routers/auth.py`).
3. **Pydantic** valida el JSON de entrada (si falta algo, responde `422` solo).
4. La funcion pide una **sesion de base de datos** y hace su trabajo.
5. Devuelve un JSON. FastAPI lo convierte y lo envia de vuelta.

Y punto. Todo lo demas es repetir esto con mas rutas.

---

## 2. Los conceptos, con palabras claras

| Concepto | Que es, en cristiano |
|---|---|
| **FastAPI** | El programa que recibe peticiones web y responde. Genera `/docs` gratis. |
| **Endpoint / ruta** | Una URL concreta (`POST /auth/login`) que hace algo. |
| **Router** | Un fichero que agrupa endpoints relacionados (`auth.py`). |
| **Uvicorn** | El "motor" que mantiene FastAPI encendido. |
| **Pydantic / schema** | Valida el JSON que **entra y sale** por la API. |
| **Modelo (SQLAlchemy)** | Una **tabla** de la base de datos escrita como clase de Python. |
| **ORM** | La capa que traduce clases de Python a SQL (`SELECT`, `INSERT`...). |
| **Dependencia (`Depends`)** | Funcion que FastAPI ejecuta **antes** de tu endpoint (ej. "comprobar el token"). |
| **JWT** | Un "pase" firmado que identifica al usuario. |
| **bcrypt / hash** | Convertir la contrasena en texto revuelto e irreversible. |

> **Modelo vs schema (confusion tipica):**
> el **modelo** es la tabla que vive en la base de datos; el **schema** es la forma del
> JSON que viaja por la red. Se parecen, pero son cosas distintas.

---

## 3. Fichero por fichero

### `Dockerfile` (la receta de la caja)

```
FROM python:3.12-slim          # parte de un Python ya instalado y ligero
WORKDIR /app                   # trabaja dentro de /app
COPY requirements.txt .        # copia la lista de librerias
RUN pip install -r requirements.txt   # las instala
COPY . .                       # copia tu codigo
CMD uvicorn app.main:app ... --reload # al arrancar: lanza FastAPI
```

- `--reload` reinicia el servidor solo cada vez que guardas un `.py`. Muy comodo para
  programar.
- `app.main:app` significa: dentro de `app/main.py`, usa el objeto llamado `app`.

### `requirements.txt` (las librerias)

Las herramientas que necesita el backend: `fastapi` y `uvicorn` (la web), `sqlalchemy` y
`psycopg2-binary` (base de datos), `pydantic-settings` (leer el `.env`),
`azure-storage-blob` (Azurite/Azure Blob), `python-jose` y `passlib[bcrypt]` + `bcrypt`
(JWT y hash), y `pytest` + `httpx` (tests).
Las versiones son **rangos** (`>=` y `<`) para no romper el proyecto al actualizar.

### `app/config.py` (leer la configuracion)

Usa `pydantic-settings` para leer el `.env` (o las variables de entorno del contenedor).
Expone un objeto `settings` con: `database_url`, `jwt_secret`, `jwt_algorithm`,
`access_token_expire_minutes`, `cors_origins`, `seed_admin`, la conexion de Azure/Azurite
y `max_upload_size_mb` (10 MB por defecto).
Asi **no escribimos secretos en el codigo**: vienen del `.env`.

### `app/database.py` (la conexion a la base de datos)

- `engine`: el "cable" que conecta con PostgreSQL.
- `SessionLocal`: una "fabrica" de conversaciones con la base de datos.
- `Base`: la clase base de la que heredan todos los modelos.
- `get_db()`: una dependencia que abre una sesion, la entrega al endpoint y **la cierra
  al terminar**. Se usa como `db: Session = Depends(get_db)`.

### `app/models.py` (las 4 tablas del ER)

Cada clase es una tabla. Aqui esta **todo el ER**:

| Modelo | Tabla | Que guarda |
|---|---|---|
| `User` | `users` | Las personas: usuario, email, hash, permisos (`can_read/write/update`), `is_admin`. |
| `File` | `files` | Cada fichero como **concepto**: dueno, nombre, tipo, version actual. **No guarda el contenido.** |
| `FileVersion` | `file_versions` | Cada **subida**: numero de version, tamano, tipo MIME, donde esta el blob (`blob_name`), fecha, quien. |
| `LogEvent` | `log_events` | El **LogBook**: quien hizo que y cuando. |

Conceptos de base de datos que aparecen:

- **PK (Primary Key)**: `id`. Identifica cada fila de forma unica.
- **FK (Foreign Key)**: una columna que apunta a otra tabla. Ej. `files.owner_id` apunta a
  `users.id`.
- **Relacion 1:N**: "uno a muchos". Un usuario tiene muchos ficheros; un fichero tiene
  muchas versiones.
- **Constraint unica**: impide repetir datos. Un usuario no puede tener dos ficheros con
  el mismo nombre (`owner_id + filename`) y un fichero no puede repetir numero de version.

> **Regla de oro del proyecto:** el **contenido** de los ficheros vive en el
> **almacenamiento** (Azurite/Azure Blob). La **informacion sobre** los ficheros (quien,
> cuando, version, tamano) vive en la **base de datos**. El backend es el unico que toca
> las dos cosas.

### `app/schemas.py` (los JSON de la API)

Define lo que entra y sale. Con `pydantic`, si mandas un JSON mal formado, FastAPI
responde `422` automaticamente.

- `UserRegister`: lo que se envia al registrarse (usuario, email y contrasena). Los
  permisos no se aceptan en el registro publico: todo usuario nuevo nace con
  `can_read=True`, `can_write=False`, `can_update=False` e `is_admin=False`.
- `UserOut`: lo que se devuelve de un usuario (**nunca** incluye la contrasena).
- `FileOut`: datos de un fichero y su version actual (`owner_id`, `owner_username`,
  `size_bytes`, `current_version`...).
- `FileVersionOut`: datos de una version concreta (`content_type`, `created_by_username`...).
- `LoginRequest`: usuario y contrasena para el login.
- `Token`: lo que devuelve el login (`access_token` + `token_type`).
- `Message`: un mensaje simple (ej. "Sesion cerrada").

### `app/security.py` (hash + JWT)

- `hash_password` / `verify_password`: convierten la contrasena en un texto revuelto
  (bcrypt) y la comprueban. Nunca se guarda la contrasena en claro.
- `create_access_token`: fabrica el JWT metiendo la identidad del usuario (`sub`) y una
  fecha de caducidad (`exp`), firmado con `jwt_secret`. Los permisos no viajan en el
  token: se consultan siempre en la base de datos.
- `decode_token`: comprueba que el token es valido y no ha caducado. Si algo falla,
  devuelve `None`.

### `app/deps.py` (dependencias reutilizables)

- `get_current_user`: mira la cabecera `Authorization: Bearer <token>`, lo verifica y
  carga el usuario de la base de datos. Si falta o es invalido, lanza `401`. Los endpoints
  que requieren estar logueado lo usan con `Depends(get_current_user)`.
- `require_permission("read" / "write" / "update")`: comprueba que el usuario tiene el
  permiso. Si no lo tiene, lanza `403`. Los endpoints de ficheros lo usan.
- `get_owned_file(db, file_id, user)`: busca un fichero del usuario actual. Si no existe
  o es de otra persona, lanza `404` (asi no se revela que ficheros existen). Un admin
  puede acceder a cualquiera.

### `app/logbook.py` (el LogBook)

Una funcion unica `write_log(db, action, username=..., resource=..., result=..., details=...)`
que **prepara** un evento en la tabla `log_events` (hace `db.add`, no `commit`). El endpoint
hace el `commit` final, de modo que el cambio de negocio y su evento de auditoria se
guardan juntos o no se guarda ninguno. Cada accion importante (login, register, upload,
download...) llama aqui. **Nico** ampliara esto con el export a CSV/JSON.

### `app/storage.py` (los blobs)

- `Storage`: interfaz con tres operaciones: `upload`, `download` y `delete`.
- `AzureBlobStorage`: implementacion real contra Azurite (local) o Azure Blob (produccion).
  Solo cambia la cadena de conexion. Crea el contenedor si no existe.
- `InMemoryStorage`: version falsa que guarda los blobs en un diccionario. Se usa en los
  tests para no depender de Azurite.
- `get_storage()`: devuelve una unica instancia cacheada. En tests se sustituye por
  `InMemoryStorage` con `dependency_overrides`.

### `app/routers/auth.py` (los endpoints de autenticacion)

| Endpoint | Que hace |
|---|---|
| `POST /auth/register` | Comprueba que no exista → hashea la contrasena → guarda el usuario → registra `REGISTER` → devuelve los datos. |
| `POST /auth/login` | Busca el usuario → comprueba la contrasena (si falla: `401` + registra `LOGIN FAIL`) → crea el JWT → registra `LOGIN`. |
| `GET /auth/me` | Devuelve los datos del usuario actual (usa `get_current_user`). |
| `POST /auth/logout` | Registra `LOGOUT`. El token caduca solo (no se puede invalidar). |

### `app/routers/files.py` (los endpoints de ficheros)

| Endpoint | Permiso | Que hace |
|---|---|---|
| `POST /files/upload` | `write` | Crea un fichero nuevo. Si el usuario ya tiene ese nombre, responde `409`. |
| `POST /files/{id}/versions` | `update` | Sube una version nueva de un fichero existente del usuario. |
| `GET /files` | `read` | Lista **solo los ficheros del usuario actual** con su version mas reciente. |
| `GET /files/{id}/download` | `read` | Devuelve la ultima version del fichero. Si es de otro usuario, responde `404`. |
| `GET /files/{id}/versions` | `read` | Lista el historial de versiones. |
| `GET /files/{id}/versions/{v}/download` | `read` | Descarga una version concreta. |
| `POST /files/{id}/versions/{v}/restore` | `update` | Restaura una version antigua creando una version nueva. |

Detalles importantes:

- El nombre se sanea (`../malo.txt` pasa a `malo.txt`) para no crear rutas raras.
- El blob se guarda como `owner/{file_id}/v{n}`.
- Crear y versionar son acciones distintas: `write` crea, `update` versiona.
- Restaurar no borra nada: copia el contenido antiguo a una version nueva.
- Si falla el storage o la base de datos, se intenta borrar el blob y se hace `rollback`.

### `app/routers/admin.py` (administracion)

| Endpoint | Que hace |
|---|---|
| `GET /admin/users` | Lista usuarios y sus permisos. |
| `PATCH /admin/users/{id}/permissions` | Cambia `can_read`, `can_write` y `can_update`. |
| `GET /admin/files` | Lista todos los ficheros de todos los usuarios. |

El admin tambien puede descargar, versionar y restaurar cualquier fichero usando los
endpoints de `/files/*`, porque `is_admin` le da bypass.

### `app/main.py` (el montaje de todo)

- Crea la app `FastAPI` con titulo y descripcion.
- Anade **CORS** (para que el frontend pueda llamar a la API desde otro origen).
- Incluye los routers de `auth`, `files` y `admin`.
- Define `GET /health` (responde `{"status": "ok"}`).
- Con `lifespan` (lo que pasa al arrancar): crea las **tablas** (`create_all`) y, si
  `SEED_ADMIN=true`, crea el usuario administrador configurado en `SEED_ADMIN_USERNAME`,
  `SEED_ADMIN_EMAIL` y `SEED_ADMIN_PASSWORD` (valores del `.env`, nunca fijos en codigo).

---

## 4. Como se relacionan los ficheros (mapa de dependencias)

```
        .env
          |  (lo lee)
          v
   app/config.py ---- settings ----+
          |                        |
          v                        v
  app/database.py  <----  app/models.py
     |        |
     |        +--> Base (lo usan los modelos)
     |        +--> SessionLocal / get_db
     v
   app/deps.py  (get_current_user, require_permission, get_owned_file)
      |   usa security.decode_token
      v
   app/routers/auth.py  (endpoints de login)
   app/routers/files.py (endpoints de ficheros)
      |   usan schemas.py (JSON)
      |   usan security.py (hash + token)
      |   usan models.py (User, File, FileVersion)
      |   usan logbook.py (preparar eventos)
      |   usan storage.py (subir/leer blobs)
      v
   app/main.py  (monta todo y arranca)

  app/schemas.py  -> define la forma de los JSON (no toca la BD)
  app/security.py -> hash y JWT (no toca la BD)
  app/logbook.py  -> prepara filas en log_events
  app/storage.py  -> guarda/lee el contenido en Azurite/Azure
```

Resumen de dependencias (quien usa a quien):

- `config` no usa a nadie (solo lee el `.env`).
- `database` usa `config`.
- `models` usa `database` (para heredar de `Base`).
- `security` usa `config`.
- `deps` usa `database`, `models` y `security`.
- `routers/auth` usa `database`, `deps`, `models`, `schemas`, `security` y `logbook`.
- `storage` usa `config` y el SDK de Azure.
- `routers/files` usa `config`, `database`, `deps`, `models`, `schemas`, `logbook` y `storage`.
- `main` usa casi todo para montar la app.

---

## 5. Flujos paso a paso

### Registro
`POST /auth/register {"username", "email", "password"}`
→ valida (Pydantic) → comprueba duplicados → `hash_password` → inserta `User` →
`write_log(REGISTER)` → devuelve los datos **sin** contrasena.

### Login (y donde entra el JWT)
`POST /auth/login {"username", "password"}`
→ busca el usuario → `verify_password` → si va bien, `create_access_token({sub})`
→ devuelve `{"access_token": "...", "token_type": "bearer"}`.

> **Como funciona el token (la pulsera).** Haces login **una vez** y el backend te da un
> **token firmado**. El frontend lo guarda y lo envia en **cada** peticion protegida en la
> cabecera `Authorization: Bearer <token>`. El backend **no recuerda** nada entre
> peticiones: solo verifica el sello (firma) y la caducidad del token. Si alguien cambia
> algo del token, la firma deja de cuadrar y se rechaza con `401`.

### Usuario actual
`GET /auth/me` con la cabecera del token → `get_current_user` valida el token y carga el
usuario → devuelve sus datos.

### Logout
`POST /auth/logout` → registra `LOGOUT`. El token **no se borra** en el servidor (JWT no
tiene estado), simplemente el frontend deja de usarlo y caduca solo.

### Crear un fichero
`POST /files/upload` con el fichero en `multipart/form-data` y el token
→ `require_permission("write")` → se comprueba el tamano → se sanea el nombre →
se rechaza si el usuario ya tiene ese nombre (`409`) → se crea el fichero y su version 1 →
se registra `UPLOAD_NEW` → `commit` → se devuelve `FileOut`.

### Subir una version
`POST /files/{id}/versions` → `require_permission("update")` → `get_owned_file`
comprueba que el fichero es del usuario (o que es admin) → se bloquea la fila de `files`
→ se sube el blob `owner/{id}/v{n}` → se crea `FileVersion` → se actualiza
`current_version` → se registra `UPLOAD_VERSION`.

### Historial y restauracion
`GET /files/{id}/versions` lista las versiones de la mas nueva a la mas antigua.
`GET /files/{id}/versions/{v}/download` descarga una version concreta.
`POST /files/{id}/versions/{v}/restore` copia el contenido de la version antigua a una
version nueva y actualiza `current_version`; no borra la version original.

### Listar y descargar
`GET /files` → `require_permission("read")` → consulta solo los ficheros del usuario →
registra `LIST` → devuelve la lista con la version actual.

`GET /files/{id}/download` → `require_permission("read")` → `get_owned_file` comprueba
que el fichero existe y es del usuario (o que es admin) → se lee el blob de la version
actual → registra `DOWNLOAD` → devuelve el contenido con `Content-Disposition`.

### Admin
`PATCH /admin/users/{id}/permissions` permite revocar `can_read`, `can_write` y
`can_update`. El admin puede listar todos los ficheros en `GET /admin/files` y operar
sobre cualquiera usando `/files/*`.

### Permisos (para los siguientes endpoints)
Un endpoint protegido se escribe asi:

```python
@router.get("/algo")
def algo(user = Depends(require_permission("read"))):
    ...
```

Si el usuario no tiene `can_read = True` → responde `403`.

---

## 6. Como arrancarlo (Docker)

Necesitas **Docker Desktop abierto** (instalado y en ejecucion). Desde la raiz del
proyecto:

```bash
docker compose up --build
```

- `--build` construye la imagen del backend (la primera vez o si cambias `requirements.txt`
  o el `Dockerfile`).
- Si solo cambias codigo, `docker compose up` basta: el `--reload` reinicia solo.

Servicios que se levantan:

| Servicio | Que es | Donde lo ves |
|---|---|---|
| `db` | PostgreSQL | puerto 5432 |
| `azurite` | Almacenamiento (emulador Azure Blob) | puerto 10000 |
| `backend` | Tu API FastAPI | http://localhost:8000/docs |
| `frontend` | Streamlit (aun no existe) | puerto 8501 |

Comandos utiles:

```bash
docker compose ps                # ver que esta corriendo
docker compose logs -f backend   # ver los errores del backend en vivo
docker compose down              # parar (los datos se conservan)
docker compose down -v           # parar y BORRAR los datos
```

---

## 7. Como probarlo

### 7.1 En el navegador (Swagger)
1. Abre **http://localhost:8000/docs**.
2. `POST /auth/register` → "Try it out" → crea `maria`.
3. `POST /auth/login` → copia el `access_token`.
4. Arriba a la derecha, boton **Authorize** → pega el token.
5. `GET /auth/me` → debe devolver tus datos.
6. Tambien hay un usuario administrador creado al arrancar con las credenciales de
   `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD` del `.env`.

### 7.2 Tests automaticos
Se ejecutan **dentro del contenedor**, contra una base de datos de prueba (`appdb_test`)
que se crea sola, para no tocar tus datos reales:

```bash
docker compose exec backend pytest
```

Los tests (`tests/test_auth.py`, `tests/test_files.py` y `tests/test_admin.py`) comprueban:
`/health`, registro + login + `/auth/me`, login con contrasena incorrecta (`401`), usuario
duplicado (`400`), `/auth/me` sin token (`401`), logout, creacion y versionado, permisos,
aislamiento entre usuarios, historial, descarga de versiones, restauracion, rollback si
falla el storage, listado global del admin, bypass del admin y revocacion de permisos.

---

## 8. Errores tipicos (y su pista)

| Sintoma | Causa habitual | Solucion |
|---|---|---|
| `docker: command not found` | Docker Desktop cerrado | Abrir Docker Desktop |
| `could not connect to server` (Postgres) | La BD aun arrancando | Esperar; el compose ya espera con `healthcheck` |
| `401` en `/auth/me` | Token ausente, mal pegado o caducado | Volver a hacer login |
| `403` en un endpoint | Usuario sin permiso | Revisar `can_read/write/update` |
| Cambio el `.env` y no pasa nada | El contenedor no se ha recreado | `docker compose up -d` (o `--build`) |
| "port is already allocated" | Puerto ocupado | Cambiar el puerto de la izquierda en el compose |

---

## 8.1 Que hace cada cosa, en una frase

- `Dockerfile` → empaqueta el backend con sus librerias.
- `requirements.txt` → lista de librerias.
- `config.py` → lee el `.env`.
- `database.py` → conecta con PostgreSQL y da sesiones.
- `models.py` → define las 4 tablas (el ER).
- `schemas.py` → define los JSON de la API.
- `security.py` → hash de contrasenas y JWT.
- `deps.py` → "quien eres" y "que permiso tienes".
- `logbook.py` → prepara la auditoria (el endpoint hace el `commit`).
- `storage.py` → guarda/lee el contenido de los ficheros.
- `routers/auth.py` → los endpoints de login.
- `routers/files.py` → crear, versionar, listar, descargar y restaurar ficheros.
- `routers/admin.py` → listar usuarios/ficheros y cambiar permisos.
- `main.py` → monta todo y arranca.

---

## 9. Que falta (siguientes pasos del equipo)

| Persona | Siguiente paso |
|---|---|
| **Ruben** | Probar versionado, historial, descarga de versiones y restauracion contra Azurite; revisar migracion/recreacion de la BD. |
| **Nico** | Ampliar `logbook.py` con el **export CSV/JSON**, `seed.py` con datos de prueba y el `security_checklist.md`. |
| **Maria** | Frontend JavaScript: login, listar, crear, versionar, historial, descargar, restaurar y panel de permisos del admin. |
| **Diego** | Dejar `docker compose up` estable, Nginx con TLS y el pipeline de CI. |

> **Contrato ya disponible** (lo que necesitara Maria):
> `POST /auth/register`, `POST /auth/login` → `{access_token, token_type}`,
> `GET /auth/me` (cabecera `Authorization: Bearer <token>`), `POST /auth/logout`,
> `GET /health`, `GET /files`, `POST /files/upload` (fichero nuevo),
> `POST /files/{id}/versions` (version nueva), `GET /files/{id}/download`,
> `GET /files/{id}/versions`, `GET /files/{id}/versions/{v}/download`,
> `POST /files/{id}/versions/{v}/restore`, `GET /admin/users`,
> `PATCH /admin/users/{id}/permissions` y `GET /admin/files`.
> Las credenciales del admin se configuran en el `.env` mediante
> `SEED_ADMIN_USERNAME` y `SEED_ADMIN_PASSWORD`.

---

## 10. Glosario corto

- **API REST**: interfaz HTTP por la que el frontend pide cosas al backend.
- **JWT**: pase firmado que identifica al usuario; contiene su identidad (`sub`), la
  caducidad (`exp`) y la firma. Los permisos se consultan en la base de datos.
- **Hash (bcrypt)**: contrasena convertida en texto revuelto e irreversible.
- **ORM (SQLAlchemy)**: traduce entre clases de Python y tablas SQL.
- **PK / FK**: clave primaria (identifica una fila) / clave foranea (apunta a otra tabla).
- **Azurite**: emulador local de Azure Blob Storage.
- **Docker / docker-compose**: empaquetar programas en cajas / levantar varias a la vez.
