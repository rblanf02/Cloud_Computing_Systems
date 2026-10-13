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
can_write (bool)              current_version               created_at
can_update(bool)                                            created_by (FK -> users.id)
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
| GET | `/files` | read | Lista ficheros con ultima version. |
| POST | `/files/upload` | write | Sube fichero (nueva version). |
| GET | `/files/{id}/download` | read | Descarga ultima version. |
| GET | `/files/{id}/versions` | read | Historial de versiones. |
| GET | `/files/{id}/versions/{v}/download` | read | Descarga una version concreta. |
| GET | `/logs` | read | Lista eventos (propios; admin: todos). |
| GET | `/logs/export?fmt=csv\|json` | read | Exporta el LogBook. |

## Flujos

**Login**: credenciales -> verify hash -> JWT (rol + permisos) -> log `LOGIN`.

**Upload** (crea version):
1. Cliente sube el fichero a `POST /files/upload`.
2. Backend comprueba permiso `write`.
3. Sube el blob `owner/{file_id}/v{n}` a Blob/Azurite.
4. Crea/actualiza `files` e inserta fila en `file_versions` (fecha, tamano, n).
5. Registra evento `UPLOAD` en `log_events`.

**Download**: comprueba `read` -> descarga binario del blob -> log `DOWNLOAD`.

**List**: lee `files` + ultima version -> lista -> log `LIST`.

**LogBook**: cada accion llama a `logbook.write_log(...)`; export a CSV/JSON.
