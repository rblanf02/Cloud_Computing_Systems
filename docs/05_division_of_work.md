# 05 - Reparto del trabajo (5 personas)

## Principios para NO depender de otros al principio

1. **Contratos congelados antes de codificar**: el modelo de datos (ER) y el contrato
   de API (OpenAPI) se escriben primero. Con eso cada persona construye su modulo
   contra el contrato, no contra el codigo de otro.
2. **Cada modulo funciona solo**: se puede probar sin el resto (Jose con Swagger,
   Ruben con un script, Maria con `USE_MOCK=true`, Nico con scripts SQL, Diego con
   Docker).
3. **Integracion al final, no al principio**: nadie espera al companero para avanzar;
   solo se unen las piezas en los hitos.
4. **Rama propia + PR**: cada uno trabaja en `feature/<nombre>`.

## Reparto por persona

### Jose - Lead tecnico + Autenticacion/API
- **Objetivo**: API base y seguridad (login/logout, JWT, roles read/write/update).
- **Entregables**: `backend/app/{main,config,database,models,schemas,security,deps}.py`,
  `routers/auth.py`, `tests/test_auth.py`.
- **Arranca SOLO**: levanta FastAPI con `uvicorn` y prueba todo desde `/docs`
  (Swagger). No necesita a nadie.
- **Bloquea a otros (solo al integrar)**: entrega el contrato de auth (endpoints y
  forma del token) para que Maria lo consuma en la fase de integracion.
- **Foco**: seguridad y el rubro "auth + autorizacion".

### Ruben - Almacenamiento + Control de versiones
- **Objetivo**: subir/descargar/listar y versionado (fecha, tamano, version).
- **Entregables**: `backend/app/storage.py`, `routers/files.py`, `backend/scripts/blob_check.py`.
- **Arranca SOLO**: script que sube y descarga un blob contra Azurite, y crea 3
  versiones; prueba sin backend ni frontend.
- **Bloquea a otros (solo al integrar)**: la tabla `file_versions` la define Nico; el
  contrato de endpoints lo fija Jose (OpenAPI). Ruben programa contra esos contratos.
- **Foco**: el rubro "muy buena nota" (versionado).

### Maria - Frontend multi-dispositivo (Streamlit)
- **Objetivo**: UI de login, listado, subida y descarga; usable en PC/tablet/movil.
- **Entregables**: `frontend/app.py`, `frontend/requirements.txt`, `frontend/Dockerfile`.
- **Arranca SOLO**: con `USE_MOCK=true` construye TODA la interfaz con datos falsos,
  sin backend. Cuando la API este lista, cambia a `USE_MOCK=false`.
- **Bloquea a otros**: a nadie. Consume el contrato OpenAPI en integracion.
- **Foco**: usabilidad y que se vea bien en los 3 dispositivos.

### Diego - Cloud / DevOps / Infra (perfil teleco)
- **Objetivo**: entorno reproducible local y despliegue en Azure con HTTPS.
- **Entregables**: `docker-compose.yml`, `backend/Dockerfile`, `infra/nginx/*`,
  `infra/terraform/*` (opcional), `.github/workflows/ci.yml`.
- **Arranca SOLO**: `docker compose up` con servicios vacios; nginx con TLS
  autofirmado; pipeline de CI. No necesita codigo de negocio.
- **Bloquea a otros**: nadie. Da el entorno donde todos corren.
- **Foco**: HTTPS/TLS, redes, contenedores, despliegue.

### Nico - Datos + LogBook + QA/Seguridad
- **Objetivo**: esquema de BD, LogBook (registro + export CSV/JSON), pruebas y
  checklist de seguridad.
- **Entregables**: `backend/app/models.py` + `logbook.py` + `routers/logs.py`,
  `backend/scripts/seed.py`, `docs/security_checklist.md`.
- **Arranca SOLO**: define el ER y un `seed.py` que inserta usuarios/ficheros/logs de
  prueba; prueba el export a CSV/JSON sin el resto.
- **Bloquea a otros**: la tabla de usuarios/versiones la usan Jose y Ruben; por eso
  Nico entrega el ER en el dia 1.
- **Foco**: auditoria (logbook = "esencial/perfecto"), calidad y seguridad.

## Semana 1 - todo en paralelo (cero dependencias)

| Persona | Tarea de la semana 1 | Verificacion propia |
|---|---|---|
| Jose | Login/JWT + `/auth/me` + tests | Probar en `/docs` |
| Ruben | `storage.py` + script subir/descargar 3 versiones | Script en Azurite |
| Maria | UI completa con `USE_MOCK=true` | `streamlit run app.py` |
| Diego | `docker compose up` + nginx TLS + CI | `curl -k https://localhost:8443` |
| Nico | ER + `seed.py` + export CSV/JSON | Ejecutar seed + export |

## Hitos de integracion

1. **H1 (fin sem 1)**: contratos (ER + OpenAPI) y docker-compose verdes.
2. **H2 (fin sem 2)**: auth + storage + logbook integrados; Maria pasa a `USE_MOCK=false`.
3. **H3 (fin sem 3)**: pruebas + seguridad + versionado validado.
4. **H4**: despliegue en Azure + HTTPS + demo.
5. **H5**: presentacion final.

## Reparto de la presentacion

| Seccion | Responsable |
|---|---|
| 1. Problem Statement | Jose |
| 2. Estado del arte + comparativa | Nico + Maria |
| 3. Specs: tecnologias/cloud | Diego |
| 3. Specs: objetivos/riesgos | Ruben |
| Diagrama general + division | Diego + Jose |

Todos exponen su parte y responden preguntas de su modulo.
