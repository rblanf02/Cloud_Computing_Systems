# 00 - Plan del proyecto

Sistema de intercambio de ficheros entre aplicaciones (PC/tablet/movil) y la nube.

## Decisiones tomadas

| Decision | Eleccion | Motivo |
|---|---|---|
| Cloud | **Azure** | Credito Azure for Students sin tarjeta; Entra ID facilita auth; Blob versioning cubre el "muy buena nota"; SDK Python de primera. |
| Backend | **FastAPI (Python)** | Equipo con perfil de datos: Python es su lenguaje fuerte; genera OpenAPI/Swagger automatico; minimo boilerplate. |
| Frontend | **Streamlit** | Un solo lenguaje, sin especialista en frontend, accesible desde navegador en los 3 dispositivos. |
| Auth | **JWT propio** | Menos configuracion que Entra ID; control total de roles para el rubro. Entra ID queda como mejora opcional. |
| Storage local | **Azurite** | Emula Azure Blob en local: se programa contra la API real sin gastar credito. |
| BD | **PostgreSQL** | Relacional, ideal para versiones y LogBook; disponible en Azure. |

## Requisitos del enunciado y como se cubren

| Requisito | Nivel | Como |
|---|---|---|
| Transferencia por HTTPS | Necesario | Nginx+self-signed en local; Container Apps/App Service con certificado gestionado en Azure. |
| Almacenamiento en la nube | Necesario | Azure Blob Storage. |
| Login + autenticacion + autorizacion (read/write/update) | Nota alta | JWT + campos `can_read/can_write/can_update` por usuario y dependencia `require_permission`. |
| Control de versiones (fecha, tamano, version) | Muy buena nota | Tabla `file_versions` + Blob versioning; cada subida crea nueva version. |
| Login / Logout / Upload / Download / List | Necesario | Endpoints `/auth/*`, `/files/*`. |
| LogBook (csv/json/xml, o BD) | Esencial/perfecto | Tabla `log_events` + export a CSV/JSON. |

## Fases

- **Fase 0** Investigacion + presentacion 1 (ver docs/01-03).
- **Fase 1** Diseno: ER, contrato OpenAPI, diagrama general.
- **Fase 2** MVP local: docker-compose (backend + frontend + Postgres + Azurite).
- **Fase 3** Funcionalidad: auth, subir/descargar/listar, versiones, logbook.
- **Fase 4** Pruebas + seguridad.
- **Fase 5** Migracion a Azure (Blob + PostgreSQL + Container Apps + TLS).
- **Fase 6** Demo + presentacion final.

## Estimacion

- Sin IA: ~7-9 semanas part-time.
- **Con IA: ~3-4 semanas part-time** (el cuello de botella pasa a ser integracion, Azure y comprension).
- La presentacion 1 se puede preparar en 2-3 dias con un prototipo minimo.

## Migracion local -> Azure (checklist)

1. Crear cuenta Azure for Students.
2. Storage Account con **Blob versioning** activado + contenedor `files`.
3. Azure Database for PostgreSQL Flexible Server.
4. Azure Container Registry (ACR) + subir imagenes de backend y frontend.
5. Container Apps (o App Service) con las variables de entorno/secrets.
6. Certificado gestionado + dominio (HTTPS).
7. Secrets en Key Vault / Container Apps secrets (nunca en el repo).
