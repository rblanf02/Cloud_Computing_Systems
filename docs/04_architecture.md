# 04 - Arquitectura

## Diagrama general

```
   PC / Tablet / Movil (navegador)                    HTTPS
              |                                          |
              v                                          v
   LOCAL (docker-compose)                      AZURE (produccion)
   +-----------+     +----------+              +----------------+   SAS   +----------------+
   | React +   |---->| FastAPI  |----+         | Container Apps |-------->| Blob Storage   |
   | Vite      |     | backend  |    |         |   (API)        |         | + versioning   |
   +-----------+     +----------+    |         +----------------+         +----------------+
         |                |          |                 |
         |                v          v                 v
         |          +-----------+  +---------+   +---------------------+
         +--------->| PostgreSQL|  | Azurite |   | PostgreSQL Flexible |
                    | + logs    |  | (blob)  |   | Server              |
                    +-----------+  +---------+   +---------------------+
                        |                                |
                     LogBook: tabla log_events + export CSV/JSON
```

En local todo entra por nginx (`https://localhost:8443`), que sirve el frontend y
redirige `/auth`, `/files`, `/logs`, `/admin`, `/health`, `/docs` y `/openapi.json`
al backend. En Azure, el HTTPS lo aporta el servicio gestionado.

## Componentes

1. **Frontend React + Vite** (`frontend/`): login/registro, ficheros propios,
   compartidos, papelera, LogBook y panel de administracion.
2. **Backend FastAPI** (`backend/`): API REST + OpenAPI; auth, permisos, ficheros,
   versiones, comparticion, papelera y logbook.
3. **Almacenamiento de objetos**: Azurite (local) / Azure Blob (cloud) con versionado.
4. **PostgreSQL**: usuarios, metadatos de ficheros, versiones, shares y eventos de log.
5. **Proxy TLS** (`infra/nginx`): HTTPS local con certificado de confianza generado con
   mkcert; en Azure lo aporta el servicio gestionado.

## Modelo de datos (ER)

```
users                         files                         file_versions
-----                         -----                         -------------
id (PK)                       id (PK)                       id (PK)
username (unique)             owner_id (FK -> users.id)     file_id (FK -> files.id)
email                         filename                      version_number
hashed_password               content_type                  size_bytes
can_read  (bool)              current_version               sha256
can_write (bool)              deleted_at (soft delete)      content_type
can_update(bool)              created_at                    blob_name
is_admin  (bool)                                            created_by (FK -> users.id)
quota_bytes (bigint)          |                             created_at
created_at                    +--- 1:N --- file_versions
                              +--- 1:N --- file_shares

file_shares
-----------
file_id (PK, FK -> files.id) | granted_to (PK, FK -> users.id)
granted_by (FK -> users.id)  | access_level (reader|editor|manager)
created_at

log_events
----------
id (PK) | timestamp | username | action | resource | result | details

user_sessions
-------------
id (PK) | user_id (FK -> users.id) | created_at | last_activity_at | revoked_at
```

## API REST (resumen)

| Metodo | Ruta | Permiso | Descripcion |
|---|---|---|---|
| POST | `/auth/register` | publico | Crea usuario con los tres permisos activos. |
| POST | `/auth/login` | publico | Crea una sesion y devuelve JWT con `sid`. |
| POST | `/auth/logout` | autenticado | Revoca la sesion actual. |
| GET | `/auth/me` | autenticado | Datos del usuario. |
| GET | `/files` | read | Lista los ficheros propios con su ultima version. |
| POST | `/files/upload` | write | Crea un fichero nuevo. |
| POST | `/files/{id}/versions` | update | Sube una version nueva. |
| GET | `/files/{id}/download` | read | Descarga la ultima version y verifica SHA-256. |
| GET | `/files/{id}/versions` | read | Historial de versiones con SHA-256. |
| GET | `/files/{id}/versions/{v}/download` | read | Descarga una version concreta. |
| POST | `/files/{id}/versions/{v}/restore` | update | Restaura una version como version nueva. |
| DELETE | `/files/{id}` | owner | Mueve el fichero a la papelera. |
| POST | `/files/{id}/restore` | owner | Restaura desde la papelera. |
| DELETE | `/files/{id}/permanent` | owner | Borra fichero, versiones y blobs. |
| GET | `/files/{id}/shares` | owner/manager | Lista accesos concedidos. |
| POST | `/files/{id}/share` | owner/manager | Comparte con otro usuario. |
| DELETE | `/files/{id}/share/{user_id}` | owner/manager | Revoca un acceso. |
| GET | `/files/shared` | autenticado | Ficheros compartidos conmigo. |
| GET | `/files/trash` | autenticado | Papelera propia. |
| GET | `/admin/users` | admin | Lista usuarios y permisos. |
| PATCH | `/admin/users/{id}/permissions` | admin | Cambia `can_read`, `can_write` y `can_update`. |
| GET | `/admin/files` | admin | Lista todos los ficheros. |
| GET | `/logs` | read | Eventos propios; el admin ve todos. |
| GET | `/logs/export?fmt=csv\|json` | read | Exporta el LogBook visible. |

## Flujos

**Login**: credenciales -> verify hash -> crea fila en `user_sessions` -> JWT con
`sub` + `sid` -> log `LOGIN`. Los permisos se leen de la base de datos en cada peticion.

**Sesion**: en cada peticion se comprueba la sesion en servidor y se actualiza
`last_activity_at`. Si pasan `SESSION_IDLE_MINUTES` (10 por defecto) sin actividad, la
sesion se revoca y el token deja de valer. `logout` marca `revoked_at` y revoca solo esa
sesion. `ACCESS_TOKEN_EXPIRE_MINUTES` es el limite maximo del JWT.

**Upload nuevo**:
1. Cliente sube el fichero a `POST /files/upload`.
2. Backend comprueba permiso `write`.
3. Rechaza si el usuario ya tiene un fichero con ese nombre (`409`).
4. Crea `files`, sube el blob `owner/{file_id}/v1` y crea `file_versions`.
5. Calcula y guarda el SHA-256 del contenido.
6. Registra `UPLOAD_NEW`.

**Nueva version**:
1. Cliente sube el fichero a `POST /files/{id}/versions`.
2. Backend comprueba permiso `update` y que el fichero es suyo.
3. Bloquea la fila de `files`, calcula `n = current_version + 1` y sube el blob.
4. Inserta `file_versions` con su SHA-256 y actualiza `current_version`.
5. Registra `UPLOAD_VERSION`.

**Download**: comprueba `read` -> descarga el blob de la version actual -> calcula
SHA-256 -> si no coincide responde `502`, registra `INTEGRITY_FAIL` y no entrega el
contenido -> si coincide registra `DOWNLOAD`.

**Historial / restore**: `GET /files/{id}/versions` lista versiones con autor y SHA-256;
descargar una version antigua requiere `read`; restaurarla requiere `update` y crea una
version nueva, sin borrar la anterior.

**Comparticion**: el propietario o un `manager` concede `reader` (leer/descargar),
`editor` (leer y subir versiones) o `manager` (ademas gestiona shares). Un usuario sin
share recibe `404` para no revelar la existencia del fichero.

**Papelera**: `DELETE /files/{id}` marca `deleted_at`; el fichero desaparece de `/files`
y aparece en `/files/trash`. `POST /files/{id}/restore` lo recupera y
`DELETE /files/{id}/permanent` borra metadatos y blobs.

**Admin**: `is_admin` da acceso total. `PATCH /admin/users/{id}/permissions` permite
revocar o devolver `can_read`, `can_write` y `can_update`; el cambio se aplica en la
siguiente peticion. El registro publico crea usuarios con los tres permisos activos.

**LogBook**: cada accion llama a `logbook.write_log(...)`; `/logs` filtra por username
salvo para el admin; el export CSV/JSON usa el mismo filtro.

**Esquema local**: al arrancar, `Base.metadata.create_all` crea tablas nuevas y
`ensure_schema()` anade de forma aditiva las columnas incorporadas despues
(`users.quota_bytes`, `files.deleted_at`, `file_versions.content_type`, `sha256`).
