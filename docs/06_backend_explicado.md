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
    deps.py             Dependencias: usuario actual y permisos
    logbook.py          Helper para escribir eventos en el LogBook
    routers/
      __init__.py
      auth.py           Endpoints: register, login, logout, me
    main.py             Monta la app, CORS, /health, crea tablas y admin
  tests/
    __init__.py
    conftest.py         Prepara la base de datos de pruebas
    test_auth.py        Pruebas del modulo de autenticacion
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
`psycopg2-binary` (base de datos), `pydantic-settings` (leer el `.env`), `python-jose` y
`passlib[bcrypt]` + `bcrypt` (JWT y hash), y `pytest` + `httpx` (tests).
Las versiones son **rangos** (`>=` y `<`) para no romper el proyecto al actualizar.

### `app/config.py` (leer la configuracion)

Usa `pydantic-settings` para leer el `.env` (o las variables de entorno del contenedor).
Expone un objeto `settings` con: `database_url`, `jwt_secret`, `jwt_algorithm`,
`access_token_expire_minutes`, `cors_origins`, `seed_admin`.
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
| `FileVersion` | `file_versions` | Cada **subida**: numero de version, tamano, donde esta el blob (`blob_name`), fecha, quien. |
| `LogEvent` | `log_events` | El **LogBook**: quien hizo que y cuando. |

Conceptos de base de datos que aparecen:

- **PK (Primary Key)**: `id`. Identifica cada fila de forma unica.
- **FK (Foreign Key)**: una columna que apunta a otra tabla. Ej. `files.owner_id` apunta a
  `users.id`.
- **Relacion 1:N**: "uno a muchos". Un usuario tiene muchos ficheros; un fichero tiene
  muchas versiones.

> **Regla de oro del proyecto:** el **contenido** de los ficheros vive en el
> **almacenamiento** (Azurite/Azure Blob). La **informacion sobre** los ficheros (quien,
> cuando, version, tamano) vive en la **base de datos**. El backend es el unico que toca
> las dos cosas.

### `app/schemas.py` (los JSON de la API)

Define lo que entra y sale. Con `pydantic`, si mandas un JSON mal formado, FastAPI
responde `422` automaticamente.

- `UserRegister`: lo que se envia al registrarse (usuario, email, contrasena, permisos).
- `UserOut`: lo que se devuelve de un usuario (**nunca** incluye la contrasena).
- `LoginRequest`: usuario y contrasena para el login.
- `Token`: lo que devuelve el login (`access_token` + `token_type`).
- `Message`: un mensaje simple (ej. "Sesion cerrada").

### `app/security.py` (hash + JWT)

- `hash_password` / `verify_password`: convierten la contrasena en un texto revuelto
  (bcrypt) y la comprueban. Nunca se guarda la contrasena en claro.
- `create_access_token`: fabrica el JWT metiendo los datos del usuario y una fecha de
  caducidad (`exp`), firmado con `jwt_secret`.
- `decode_token`: comprueba que el token es valido y no ha caducado. Si algo falla,
  devuelve `None`.

### `app/deps.py` (dependencias reutilizables)

- `get_current_user`: mira la cabecera `Authorization: Bearer <token>`, lo verifica y
  carga el usuario de la base de datos. Si falta o es invalido, lanza `401`. Los endpoints
  que requieren estar logueado lo usan con `Depends(get_current_user)`.
- `require_permission("read" / "write" / "update")`: comprueba que el usuario tiene el
  permiso. Si no lo tiene, lanza `403`. Ruben lo usara en los endpoints de ficheros.

### `app/logbook.py` (el LogBook)

Una funcion unica `write_log(db, action, username=..., resource=..., result=..., details=...)`
que inserta un evento en la tabla `log_events`. Cada accion importante
(login, register, upload, download...) llama aqui. **Nico** ampliara esto con el export a
CSV/JSON.

### `app/routers/auth.py` (los endpoints de autenticacion)

| Endpoint | Que hace |
|---|---|
| `POST /auth/register` | Comprueba que no exista → hashea la contrasena → guarda el usuario → registra `REGISTER` → devuelve los datos. |
| `POST /auth/login` | Busca el usuario → comprueba la contrasena (si falla: `401` + registra `LOGIN FAIL`) → crea el JWT → registra `LOGIN`. |
| `GET /auth/me` | Devuelve los datos del usuario actual (usa `get_current_user`). |
| `POST /auth/logout` | Registra `LOGOUT`. El token caduca solo (no se puede invalidar). |

### `app/main.py` (el montaje de todo)

- Crea la app `FastAPI` con titulo y descripcion.
- Anade **CORS** (para que el frontend pueda llamar a la API desde otro origen).
- Incluye el router de `auth`.
- Define `GET /health` (responde `{"status": "ok"}`).
- Con `lifespan` (lo que pasa al arrancar): crea las **tablas** (`create_all`) y, si
  `SEED_ADMIN=true`, crea el usuario **admin / admin123**.

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
  app/deps.py  (get_current_user, require_permission)
     |   usa security.decode_token
     v
  app/routers/auth.py  (endpoints)
     |   usa schemas.py (JSON)
     |   usa security.py (hash + token)
     |   usa models.py (User)
     |   usa logbook.py (escribir eventos)
     v
  app/main.py  (monta todo y arranca)

  app/schemas.py  -> define la forma de los JSON (no toca la BD)
  app/security.py -> hash y JWT (no toca la BD)
  app/logbook.py  -> escribe en la tabla log_events
```

Resumen de dependencias (quien usa a quien):

- `config` no usa a nadie (solo lee el `.env`).
- `database` usa `config`.
- `models` usa `database` (para heredar de `Base`).
- `security` usa `config`.
- `deps` usa `database`, `models` y `security`.
- `routers/auth` usa `database`, `deps`, `models`, `schemas`, `security` y `logbook`.
- `main` usa casi todo para montar la app.

---

## 5. Flujos paso a paso

### Registro
`POST /auth/register {"username", "email", "password"}`
→ valida (Pydantic) → comprueba duplicados → `hash_password` → inserta `User` →
`write_log(REGISTER)` → devuelve los datos **sin** contrasena.

### Login (y donde entra el JWT)
`POST /auth/login {"username", "password"}`
→ busca el usuario → `verify_password` → si va bien, `create_access_token({sub, is_admin})`
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

### Permisos (para Ruben y siguientes)
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
6. Tambien hay el usuario **admin / admin123** (creado al arrancar).

### 7.2 Tests automaticos
Se ejecutan **dentro del contenedor**, contra una base de datos de prueba (`appdb_test`)
que se crea sola, para no tocar tus datos reales:

```bash
docker compose exec backend pytest
```

Los tests (`tests/test_auth.py`) comprueban: `/health`, registro + login + `/auth/me`,
login con contrasena incorrecta (`401`), usuario duplicado (`400`), `/auth/me` sin token
(`401`) y logout.

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
- `logbook.py` → escribe la auditoria.
- `routers/auth.py` → los endpoints de login.
- `main.py` → monta todo y arranca.

---

## 9. Que falta (siguientes pasos del equipo)

| Persona | Siguiente paso |
|---|---|
| **Ruben** | `storage.py` (Azurite/Azure Blob) + endpoints `/files/*` usando `require_permission("write"/"read")`. |
| **Nico** | Ampliar `logbook.py` con el **export CSV/JSON**, `seed.py` con datos de prueba y el `security_checklist.md`. |
| **Maria** | App **Streamlit** (login, listar, subir, descargar) consumiendo estos endpoints. |
| **Diego** | Dejar `docker compose up` estable, Nginx con TLS y el pipeline de CI. |

> **Contrato de auth ya disponible** (lo que necesitara Maria):
> `POST /auth/register`, `POST /auth/login` → `{access_token, token_type}`,
> `GET /auth/me` (cabecera `Authorization: Bearer <token>`), `POST /auth/logout`,
> `GET /health`. El usuario admin por defecto es **admin / admin123**.

---

## 10. Glosario corto

- **API REST**: interfaz HTTP por la que el frontend pide cosas al backend.
- **JWT**: pase firmado que identifica al usuario; contiene permisos y caduca.
- **Hash (bcrypt)**: contrasena convertida en texto revuelto e irreversible.
- **ORM (SQLAlchemy)**: traduce entre clases de Python y tablas SQL.
- **PK / FK**: clave primaria (identifica una fila) / clave foranea (apunta a otra tabla).
- **Azurite**: emulador local de Azure Blob Storage.
- **Docker / docker-compose**: empaquetar programas en cajas / levantar varias a la vez.
