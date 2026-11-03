# 04 - Arquitectura

## Diagrama general

```
   PC / Tablet / Movil (navegador)                    HTTPS
              |                                          |
              v                                          v
   LOCAL (docker-compose)                      AZURE (produccion)
   +-----------+     +----------+              +----------------+   SAS   +----------------+
   | Streamlit |---->| FastAPI  |----+         | Container Apps |-------->| Blob Storage   |
   | frontend  |     | backend  |    |         |   (API)        |         | + versioning   |
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

## Componentes

1. **Frontend Streamlit** (`frontend/`): UI de login, listado, subida y descarga.
2. **Backend FastAPI** (`backend/`): API REST + OpenAPI; auth, permisos, ficheros, logbook.
3. **Almacenamiento de objetos**: Azurite (local) / Azure Blob (cloud) con versionado.
4. **PostgreSQL**: usuarios, metadatos de ficheros, versiones y eventos de log.
5. **Proxy TLS** (`infra/nginx`): HTTPS local con certificado autofirmado; en Azure lo
   aporta el servicio gestionado.

## Modelo de datos (ER)

```
users                         files                         file_versions
-----                         -----                         -------------
id (PK)                       id (PK)                       id (PK)
username (unique)             owner_id (FK -> users.id)     file_id (FK -> files.id)
email                         filename                      version_number
hashed_password               content_type                  size_bytes
can_read  (bool)              created_at                    blob_name
can_write (bool)              current_version               content_type
can_update(bool)                                            created_at
is_admin  (bool)                                            created_by (FK -> users.id)
created_at                    |                             |
                              +--- 1:N --- file_versions

log_events
----------
id (PK) | timestamp | username | action | resource | result | details
```

## API REST (resumen)

| Metodo | Ruta | Permiso | Descripcion |
|---|---|---|---|
| POST | `/auth/register` | publico | Crea usuario. |
| POST | `/auth/login` | publico | Devuelve JWT. |
| POST | `/auth/logout` | autenticado | Registra logout. |
| GET | `/auth/me` | autenticado | Datos del usuario. |
| GET | `/files` | read | Lista los ficheros del usuario con su ultima version. |
| POST | `/files/upload` | write | Crea un fichero nuevo. |
| POST | `/files/{id}/versions` | update | Sube una version nueva de un fichero existente. |
| GET | `/files/{id}/download` | read | Descarga la ultima version. |
| GET | `/files/{id}/versions` | read | Historial de versiones. |
| GET | `/files/{id}/versions/{v}/download` | read | Descarga una version concreta. |
| POST | `/files/{id}/versions/{v}/restore` | update | Restaura una version como version nueva. |
| GET | `/admin/users` | admin | Lista usuarios y permisos. |
| PATCH | `/admin/users/{id}/permissions` | admin | Cambia `can_read`, `can_write` y `can_update`. |
| GET | `/admin/files` | admin | Lista todos los ficheros. |
| GET | `/logs` | read | Lista eventos (propios; admin: todos). |
| GET | `/logs/export?fmt=csv\|json` | read | Exporta el LogBook. |

## Flujos

**Login**: credenciales -> verify hash -> JWT (identidad + caducidad) -> log `LOGIN`.
Los permisos se leen de la base de datos en cada peticion.

**Upload nuevo**:
1. Cliente sube el fichero a `POST /files/upload`.
2. Backend comprueba permiso `write`.
3. Rechaza si el usuario ya tiene un fichero con ese nombre (`409`).
4. Crea `files`, sube el blob `owner/{file_id}/v1` y crea `file_versions`.
5. Registra `UPLOAD_NEW`.

**Nueva version**:
1. Cliente sube el fichero a `POST /files/{id}/versions`.
2. Backend comprueba permiso `update` y que el fichero es suyo.
3. Bloquea la fila de `files`, calcula `n = current_version + 1` y sube el blob.
4. Inserta `file_versions` y actualiza `current_version`.
5. Registra `UPLOAD_VERSION`.

**Download**: comprueba `read` -> descarga el blob de la version actual -> log `DOWNLOAD`.

**Historial / restore**: `GET /files/{id}/versions` lista versiones; descargar una version
antigua requiere `read`; restaurarla requiere `update` y crea una version nueva, sin borrar
la anterior.

**Admin**: `is_admin` da acceso total. `PATCH /admin/users/{id}/permissions` permite
revocar `can_read`, `can_write` y `can_update`; el cambio se aplica en la siguiente peticion.

**LogBook**: cada accion llama a `logbook.write_log(...)`; export a CSV/JSON.
