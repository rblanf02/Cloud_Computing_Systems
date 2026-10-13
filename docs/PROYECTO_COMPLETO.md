# Documento maestro del proyecto - CloudFile Exchange

> **Proposito de este documento.** Es un unico documento autocontenido que explica
> **todo** el proyecto: que se pide, que se decidio y por que, las tecnologias
> definitivas, la arquitectura, como se relacionan todas las piezas entre si, el
> reparto entre los 5 integrantes y el plan. Esta escrito para que puedas
> **enviarselo a una IA y que te lo explique de principio a fin** sin falta de
> contexto externo. Al final hay un indice y un glosario.

---

## 1. Resumen ejecutivo

**CloudFile Exchange** es un sistema de **intercambio de ficheros** (documentos y
fotos) entre aplicaciones de usuario (PC, tablet, movil) y un sistema en la nube.
Los usuarios pueden **iniciar sesion, subir, descargar y listar** ficheros; el sistema
aplica **autenticacion y autorizacion** (permisos de lectura, escritura y
actualizacion), mantiene un **control de versiones** (fecha, tamano y numero de
version de cada fichero) y registra todas las operaciones en un **LogBook**
(auditoria) exportable a CSV/JSON.

Es un proyecto de la asignatura **Cloud Computing Systems**. El objetivo es disenar y
construir el sistema, probarlo **primero en local** (con Docker) y despues
**desplegarlo en la nube (Azure) con HTTPS**.

**Resultado esperado:** un prototipo funcional con las 6 capacidades pedidas, mas
permisos por rol, versionado y auditoria, demostrable y desplegado en Azure.

---

## 2. Enunciado original y requisitos

El enunciado pide: *"Design a data exchange system (documents, photos) between the
application (computer, tablet, smartphone) and the cloud system."*

### 2.1 Supuestos del sistema (con su nivel de exigencia)

| Requisito del enunciado | Nivel | Como se cubre |
|---|---|---|
| Transferencia de ficheros por HTTPS | **Necesario** | TLS en el proxy (local) y certificado gestionado en Azure |
| Ficheros almacenados en la nube (Azure/AWS/GCP) | **Necesario** | Azure Blob Storage |
| Login, autenticacion y autorizacion (read/write/update) | **Nota alta** | JWT + permisos por usuario |
| Control de versiones (fecha, tamano, version) | **Muy buena nota** | Tabla de versiones + Blob versioning |

### 2.2 Capacidades del sistema

- Login.
- Logout.
- Descargar fichero.
- Subir fichero.
- Leer listado de ficheros.
- **LogBook**: registro de logins y operaciones. *Esencial* en fichero de texto
  (CSV/JSON/XML); *perfecto* en base de datos.

### 2.3 Requisitos de la primera presentacion

La presentacion debe incluir:

1. **Problem Statement / idea**: reto (challenge), enfoque (approach) y resultado
   (outcome).
2. **Estado del arte**: investigacion (metodos y fuentes), trabajo relacionado
   (soluciones existentes y sus ventajas/inconvenientes) y **comparativa detallada de
   las 3 soluciones mas similares**.
3. **Especificaciones y requisitos**: objetivos, fuentes, herramientas/tecnologias
   (con justificacion), riesgos y medidas de exito.

Notas del profesor (de sus apuntes): *decidir el cloud, las tecnologias del
proveedor, una arquitectura pequena, usar docker-compose para una mini prueba en
local antes de moverlo a la nube, un diagrama del sistema, y explicar como se divide
el trabajo.*

---

## 3. Decisiones de diseno (definitivas) y su justificacion

### 3.1 Cloud: **Azure**

Se elige **Azure** entre AWS y Azure por encaje con el equipo (mayoria de perfil
cientifico-de-datos, 1 desarrollador de software, 1 de telecomunicaciones):

| Motivo | Detalle |
|---|---|
| Coste | **Azure for Students** da credito sin tarjeta de credito. |
| Autenticacion | **Microsoft Entra ID** disponible para simplificar login/roles (aunque el MVP usa JWT propio). |
| Versionado | **Blob Storage con versioning** cubre el requisito de "muy buena nota". |
| Integracion | SDK de Python de primer nivel y buena integracion con VS Code. |
| Despliegue | Container Apps / App Service con certificado HTTPS gestionado. |

> AWS seria igualmente valido (S3 con versioning nativo). Migrar seria cambiar la
> capa de almacenamiento a `boto3`/S3.

### 3.2 Stack: **Python de punta a punta**

El criterio fue **el stack mas sencillo para el equipo**:
- **Backend FastAPI**: Python es el lenguaje fuerte del equipo; genera documentacion
  OpenAPI/Swagger automatica (ideal para repartir trabajo); minimo boilerplate.
- **Frontend Streamlit**: un unico lenguaje; no hace falta especialista en frontend;
  accesible desde el navegador en PC, tablet y movil (cubre "computer, tablet,
  smartphone" con un solo desarrollo).
- **Autenticacion JWT propia** (en vez de Entra ID) para el MVP: menos configuracion
  externa y control total de los roles. Entra ID queda como mejora opcional.

---

## 4. Tecnologias definitivas

| Capa | Tecnologia | Por que |
|---|---|---|
| Cloud | Azure | Credito students, Blob versioning, Entra ID, SDK Python |
| Backend / API | Python + **FastAPI** | Rapido, Python, Swagger automatico |
| Servidor | Uvicorn | Servidor ASGI estandar para FastAPI |
| Autenticacion | **JWT** (python-jose) + **bcrypt** (passlib) | Estandar, sencillo, control de roles |
| Base de datos | **PostgreSQL** | Relacional, ideal para versiones y auditoria |
| ORM | SQLAlchemy | Mapeo objeto-relacional maduro |
| Validacion/config | Pydantic + pydantic-settings | Validacion de datos y variables de entorno |
| Almacenamiento de objetos | **Azure Blob Storage** (prod) / **Azurite** (local) | Versionado + emulacion local sin coste |
| SDK de storage | azure-storage-blob | Cliente oficial de Azure |
| Frontend | **Streamlit** | UI rapida en Python, multi-dispositivo |
| Contenedores | **Docker** + **docker-compose** | Entorno reproducible (requisito del profesor) |
| Proxy / TLS local | Nginx + certificado autofirmado | HTTPS en local |
| CI/CD | **GitHub Actions** | Ejecuta tests automaticamente |
| IaC (opcional) | Terraform | Despliegue reproducible en Azure (sube nota) |

---

## 5. Arquitectura: como se relaciona todo

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
                        |
                     LogBook: tabla log_events + export CSV/JSON
```

### 5.1 Componentes y su relacion

1. **Frontend (Streamlit)** - Interfaz de usuario. Se comunica **solo** con el
   backend por HTTP(S). Muestra login, listado, subida, descarga y el LogBook.
2. **Backend (FastAPI)** - El "cerebro". Recibe las peticiones, **autentica**
   (comprueba el JWT), **autoriza** (comprueba permisos), y coordina el resto:
   - Habla con **PostgreSQL** para usuarios, metadatos, versiones y logbook.
   - Habla con **Blob Storage / Azurite** para guardar y leer los ficheros.
3. **Almacenamiento de objetos (Blob/Azurite)** - Guarda el **contenido** de los
   ficheros. En local se usa **Azurite** (emulador de Azure Blob); en produccion,
   **Azure Blob Storage**. Solo cambia la cadena de conexion.
4. **Base de datos (PostgreSQL)** - Guarda usuarios, permisos, **metadatos** de
   ficheros, el **historial de versiones** y el **LogBook**.
5. **Proxy TLS (Nginx / servicio gestionado)** - Termina el HTTPS y reparte el
   trafico entre frontend y API.

### 5.2 Regla de oro de las relaciones

- El **contenido** de los ficheros vive en el **almacenamiento de objetos**.
- La **informacion sobre** los ficheros (quien, cuando, version, tamano) vive en la
  **base de datos**.
- El **backend** es el unico que toca ambos y el unico que decide **quien puede que**.
- El **frontend nunca** toca la base de datos ni el almacenamiento directamente.

---

## 6. Modelo de datos (ER)

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
is_admin  (bool)
created_at                    |                             |
                              +--- 1:N --- file_versions

log_events
----------
id (PK) | timestamp | username | action | resource | result | details
```

Relaciones:
- `users 1:N files` (un usuario tiene muchos ficheros).
- `files 1:N file_versions` (un fichero tiene muchas versiones).
- `log_events` es independiente: registra eventos de cualquier usuario/accion.

---

## 7. Contrato de la API REST

| Metodo | Ruta | Permiso | Descripcion |
|---|---|---|---|
| POST | `/auth/register` | publico | Crea un usuario. |
| POST | `/auth/login` | publico | Devuelve un token JWT. |
| POST | `/auth/logout` | autenticado | Registra el cierre de sesion. |
| GET | `/auth/me` | autenticado | Datos del usuario actual. |
| GET | `/files` | read | Lista los ficheros del usuario con su ultima version. |
| POST | `/files/upload` | write | Sube un fichero (crea una nueva version). |
| GET | `/files/{id}/download` | read | Descarga la ultima version. |
| GET | `/files/{id}/versions` | read | Historial de versiones. |
| GET | `/files/{id}/versions/{v}/download` | read | Descarga una version concreta. |
| GET | `/logs` | read | Lista eventos (propios; admin ve todos). |
| GET | `/logs/export?fmt=csv\|json` | read | Exporta el LogBook. |
| GET | `/health` | publico | Comprobacion de estado. |

> FastAPI genera automaticamente la documentacion de esta API en `/docs`
> (Swagger UI), lo que sirve como contrato vivo entre frontend y backend.

---

## 8. Flujos principales

**Login**
1. El usuario envia usuario y contrasena.
2. El backend comprueba el hash de la contrasena (bcrypt).
3. Si es correcto, firma un **JWT** con el usuario y sus permisos.
4. Registra `LOGIN` en el LogBook.

**Upload (crea una version)**
1. El usuario sube el fichero a `POST /files/upload`.
2. El backend comprueba el permiso `write`.
3. Sube el contenido al blob con nombre `owner/{file_id}/v{n}`.
4. Actualiza/crea la fila en `files` e inserta una fila en `file_versions`
   (fecha, tamano, numero de version).
5. Registra `UPLOAD` en el LogBook.

**Download**
1. El backend comprueba el permiso `read`.
2. Descarga el contenido del blob de la version pedida.
3. Registra `DOWNLOAD` en el LogBook y lo devuelve.

**List**
1. El backend lee los ficheros del usuario y su ultima version.
2. Registra `LIST` en el LogBook.

**LogBook**
- Cada accion llama a un unico helper `write_log(...)`.
- Se puede exportar todo el historial a **CSV** o **JSON**.

---

## 9. Seguridad

- **Contrasenas**: nunca en claro; se guardan con hash **bcrypt**.
- **Sesiones**: **JWT** firmado con una clave secreta; incluye caducidad.
- **Autorizacion**: cada endpoint declara el permiso requerido
  (`read`/`write`/`update`) mediante una dependencia reutilizable.
- **Transporte**: **HTTPS/TLS** obligatorio.
- **Secretos**: fuera del repositorio (`.env` local; Key Vault / secrets en Azure).
- **Validacion**: Pydantic valida las entradas; se controlan tipos de fichero.
- **Buenas practicas**: CORS configurado, minimo privilegio por usuario.

---

## 10. Control de versiones (requisito de "muy buena nota")

- Cada **subida** de un fichero existente crea una **nueva version**.
- Se guarda por version: **fecha**, **tamano** y **numero de version**.
- Se implementa en **dos capas**:
  1. **Blob por version**: cada version es un objeto distinto
     (`owner/{file_id}/v{n}`), lo que hace el historial explicito.
  2. **Blob versioning de Azure**: capa extra de seguridad a nivel de cuenta
     (recomendado activarlo en produccion).
- El usuario puede **listar** el historial y **descargar cualquier version**.

---

## 11. LogBook (requisito "esencial/perfecto")

- Registra **logins** (incluidos los fallidos) y **operaciones** (upload, download,
  list, etc.) con: fecha/hora, usuario, accion, recurso, resultado y detalles.
- Se guarda en **base de datos** (cumple el nivel "perfecto"), pero es **exportable**
  a **CSV** y **JSON** (cumple tambien el nivel "esencial" en fichero de texto).

---

## 12. Entornos y migracion local -> Azure

**Entorno local (docker-compose)**: backend + frontend + PostgreSQL + Azurite
(emulador de Blob) + Nginx con TLS opcional. Se desarrolla y prueba **sin coste**.

**Produccion (Azure)**: Container Apps (API) + Blob Storage (con versioning) +
PostgreSQL Flexible Server + Container Registry + certificado gestionado HTTPS.

**Migracion (checklist)**:
1. Crear cuenta Azure for Students.
2. Storage Account con **Blob versioning** activado + contenedor `files`.
3. Azure Database for PostgreSQL Flexible Server.
4. Azure Container Registry y subir las imagenes.
5. Container Apps con variables de entorno/secrets.
6. Certificado gestionado + dominio (HTTPS).
7. Secrets en Key Vault / Container Apps (nunca en el repositorio).

> La clave: el codigo es el mismo; solo cambian las **credenciales/endpoints** de
> base de datos y almacenamiento.

---

## 13. Reparto del trabajo (5 personas)

### 13.1 Principios para NO depender de otros al principio

1. **Contratos congelados antes de codificar**: el modelo de datos (ER) y el contrato
   de la API (OpenAPI) se definen primero. Cada persona construye contra el contrato,
   no contra el codigo de otro.
2. **Cada modulo funciona solo** y se puede probar aislado.
3. **Integracion al final**; nadie espera a un companero para avanzar.
4. **Rama propia + PR** por persona.

### 13.2 Roles y responsabilidades

| Persona | Rol | Responsabilidad principal | Entregables |
|---|---|---|---|
| **Jose** | Lead tecnico + Auth | Login/logout, JWT, permisos, API base | Modulos de auth, contrato OpenAPI, tests |
| **Ruben** | Storage + Versionado | Subir/descargar/listar, versionado | Capa de almacenamiento, endpoints de ficheros |
| **Maria** | Frontend | UI multi-dispositivo | App Streamlit (login, listar, subir, descargar) |
| **Diego** | Cloud / DevOps | Docker, Azure, HTTPS, CI/CD | docker-compose, despliegue, TLS, pipeline |
| **Nico** | Datos + LogBook + QA | Esquema BD, LogBook, pruebas, seguridad | Modelo ER, logbook+export, tests, checklist |

### 13.3 Como se complementan

- Jose fija el **contrato de la API**; Diego da el **entorno comun**; Nico define la
  **base de datos**. Con eso, Maria y Ruben trabajan **en paralelo sin bloquearse**.
- Revisiones cruzadas de codigo entre companeros.

### 13.4 Semana 1: todo en paralelo (cero dependencias)

| Persona | Tarea de la semana 1 | Verificacion propia |
|---|---|---|
| Jose | Login/JWT + `/auth/me` + tests | Probar en `/docs` |
| Ruben | Storage + subir/descargar 3 versiones | Script contra Azurite |
| Maria | UI completa con datos de prueba (mock) | `streamlit run` |
| Diego | `docker compose up` + Nginx TLS + CI | `curl -k https://localhost:8443` |
| Nico | ER + datos de prueba + export CSV/JSON | Ejecutar seed + export |

### 13.5 Hitos de integracion

1. **H1**: contratos (ER + OpenAPI) y docker-compose funcionando.
2. **H2**: auth + storage + logbook integrados; Maria pasa de mock a API real.
3. **H3**: pruebas + seguridad + versionado validado.
4. **H4**: despliegue en Azure + HTTPS + demo.
5. **H5**: presentacion final.

### 13.6 Reparto de la presentacion

| Seccion | Responsable |
|---|---|
| 1. Problem Statement | Jose |
| 2. Estado del arte + comparativa | Nico + Maria |
| 3. Specs: tecnologias/cloud | Diego |
| 3. Specs: objetivos/riesgos | Ruben |
| Diagrama general + division | Diego + Jose |

Todos exponen su parte y responden preguntas de su modulo.

---

## 14. Plan de fases y estimacion

| Fase | Contenido |
|---|---|
| Fase 0 | Investigacion + presentacion 1 |
| Fase 1 | Diseno (ER, OpenAPI, diagrama) |
| Fase 2 | MVP local con docker-compose |
| Fase 3 | Funcionalidad (auth, ficheros, versiones, logbook) |
| Fase 4 | Pruebas + seguridad |
| Fase 5 | Migracion a Azure + HTTPS |
| Fase 6 | Demo + presentacion final |

**Estimacion**: ~7-9 semanas part-time sin ayuda de IA; **~3-4 semanas part-time con
IA** como acelerador. El cuello de botella pasa a ser integracion, Azure y comprension.
La 1a presentacion puede prepararse en 2-3 dias con un prototipo minimo.

---

## 15. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Fuga de credenciales / secrets | Alto | `.env` fuera del repo; Key Vault en Azure |
| Sobrecoste cloud | Medio | Azure for Students; Azurite local; apagar recursos |
| Curva de aprendizaje (Docker/Azure) | Medio | Local primero; plantillas; IA como apoyo |
| Errores de configuracion TLS/CORS | Medio | Checklist; probar HTTPS en local |
| Perdida de datos | Alto | Versionado; backups |
| Scope creep | Medio | Limites definidos |

---

## 16. Medidas de exito

- [ ] Las 6 capacidades funcionan: login, logout, upload, download, list, logbook.
- [ ] Autenticacion y autorizacion read/write/update verificadas con pruebas.
- [ ] Subir 3 veces un fichero genera 3 versiones con fecha y tamano.
- [ ] LogBook exportable a CSV y JSON.
- [ ] Transferencia por HTTPS con certificado valido en la nube.
- [ ] Despliegue funcional en Azure + demo en vivo.
- [ ] Coste dentro del credito.

---

## 17. Estado del arte (resumen para la presentacion)

**Investigacion**: documentacion oficial de Azure/AWS, OWASP, RFC 7519 (JWT) y
RFC 8446 (TLS), y analisis de productos existentes.

**Trabajo relacionado**: Google Drive, Dropbox, Microsoft OneDrive/SharePoint y
Nextcloud (open source autoalojable).

**Comparativa de las 3 mas cercanas** (criterios del enunciado):

| Criterio | Google Drive | Dropbox | OneDrive/SharePoint |
|---|---|---|---|
| HTTPS | Si | Si | Si |
| Almacenamiento cloud | Si | Si | Si |
| Autenticacion | Google (OAuth2) | Dropbox | Microsoft / Entra ID |
| Permisos | Por archivo/carpeta | Por archivo/carpeta | Por rol, muy detallado |
| Versionado | Si (historial) | Si (historial) | Si (historial) |
| LogBook/auditoria | Limitado | Planes avanzados | Avanzado (corporativo) |
| Codigo abierto | No | No | No |

**Conclusion**: los comerciales ya resuelven el problema a gran escala, pero son
"caja negra" y dependientes del proveedor. Nuestro proyecto **construye** ese sistema
sobre Azure con **control total** de autenticacion, permisos, versionado y LogBook,
que es lo que pide el enunciado. Nextcloud es la referencia mas cercana en filosofia
(control propio) pero exige gestionar servidores.

---

## 18. Estructura de la presentacion (slides)

1. Portada (titulo + integrantes).
2. Idea/Problema (Jose).
3. Approach (Jose).
4. Outcome esperado (Jose).
5. Estado del arte: investigacion (Nico).
6. Soluciones existentes (Nico).
7. Comparativa de las 3 mas cercanas (Nico + Maria).
8. Conclusion del estado del arte (Maria).
9. Objetivos y limites (Ruben).
10. Riesgos (Ruben).
11. Tecnologias y justificacion (Diego).
12. Cloud elegido: Azure (Diego).
13. Diagrama general (Diego + Jose).
14. Division del trabajo (Jose).
15. Medidas de exito (Maria).
16. Demo / prototipo y cierre.

---

## 19. Glosario

- **API REST**: interfaz HTTP por la que el frontend pide cosas al backend.
- **JWT (JSON Web Token)**: "pase" firmada que identifica al usuario; contiene sus
  permisos y caduca.
- **Blob / almacenamiento de objetos**: servicio para guardar archivos por trozos
  (Azure Blob Storage; Azurite es su emulador local).
- **Blob versioning**: funcion de Azure que guarda versiones de cada objeto.
- **Azurite**: emulador local de Azure Blob Storage (gratis, sin nube).
- **PostgreSQL**: base de datos relacional.
- **ORM (SQLAlchemy)**: capa que traduce entre objetos Python y tablas SQL.
- **FastAPI / Uvicorn**: framework web de Python / su servidor.
- **Streamlit**: libreria para crear interfaces web en Python.
- **Docker / docker-compose**: empaquetado en contenedores / orquestacion local.
- **TLS/HTTPS**: cifrado del trafico en red.
- **LogBook**: registro/auditoria de accesos y operaciones.
- **CI/CD**: integracion y despliegue continuos (GitHub Actions).

---

## 20. Supuestos y preguntas abiertas

- Se asume un **prototipo** academico, no un producto de produccion masivo.
- La **fecha exacta y la rubrica** de la presentacion hay que confirmarlas con el
  profesor.
- Se asume que el enunciado acepta **Azure** como proveedor (lo lista primero).
- Entra ID queda como **mejora opcional** sobre el JWT propio del MVP.
- Legal/GDPR: al tratar fotos y documentos (datos personales), conviene un aviso de
  privacidad y borrado en versiones futuras.

---

# PARTE II - GUIA PARA PRINCIPIANTES: cosas importantes a tener en cuenta

> Asumimos que es vuestro **primer proyecto** de este tipo. Aqui esta todo lo que
> suele pillar por sorpresa. Leerlo **antes** de empezar y tenerlo a mano.

## 21. Herramientas que hay que instalar

- **Git** (control de versiones).
- **VS Code** (editor; instalar extensiones de Python y Docker).
- **Docker Desktop** (incluye Docker y `docker compose`). **En Windows debe estar
  ABIERTO y ejecutandose**; si esta cerrado, el comando `docker` no existe.
- **Python 3.12** (solo si quereis probar cosas fuera de Docker).
- **Azure CLI** (`az`) para desplegar en Azure (fase final).
- Cuenta de **GitHub** y, para el final, cuenta **Azure for Students**.

## 22. Que es Docker y docker-compose (en cristiano)

- Una **imagen** es una "receta" empaquetada (por ejemplo, "Python + mis
  dependencias").
- Un **contenedor** es esa receta **ejecutandose**.
- **docker-compose** levanta varios contenedores a la vez y los conecta en una red
  interna. Nuestro `docker-compose.yml` define estos servicios:

| Servicio | Que es | Puerto en tu PC |
|---|---|---|
| `db` | PostgreSQL | 5432 |
| `azurite` | Emulador de Azure Blob (local) | 10000 |
| `backend` | API FastAPI | 8000 |
| `frontend` | App Streamlit | 8501 |
| `nginx` | Proxy HTTPS (opcional) | 8443 |

### Comandos que usareis todo el rato

```powershell
docker compose up --build        # levanta todo (y reconstruye imagenes)
docker compose up -d             # en segundo plano (no ocupa la terminal)
docker compose logs -f backend   # ver logs de un servicio en vivo
docker compose ps                # ver que contenedores estan corriendo
docker compose exec backend bash # entrar "dentro" de un contenedor
docker compose down              # parar y borrar contenedores (los datos se guardan)
docker compose down -v           # parar y BORRAR tambien los datos (volumenes)
docker compose --profile tls up  # levantar tambien el nginx con HTTPS
```

## 23. Las 5 cosas que MAS confunden al principio

1. **`localhost` NO es lo mismo que el nombre del servicio.** Dentro de la red de
   Docker, el backend encuentra la base de datos en `db` y el emulador en `azurite`
   (por eso en `.env` la URL es `...@db:5432/...`). Desde **tu navegador**, en cambio,
   si es `localhost:8501`. Confundirlo es el error numero 1.
2. **`up` vs `up --build`.** Si cambias el codigo o `requirements.txt`, no basta con
   reiniciar: hay que reconstruir (`--build`).
3. **`down` NO borra datos, `down -v` SI.** Los volumenes (`pgdata`, `azurite`) hacen
   que los datos sobrevivan. Usa `-v` solo cuando quieras empezar de cero.
4. **Los puertos son "de tu PC : del contenedor".** Si algo no abre, probablemente
   ese puerto ya lo usa otro programa (cambia el de la izquierda).
5. **El `.env` no se sube a Git.** El `.env.example` si (es la plantilla). Los
   secretos no van al repositorio **nunca**.

## 24. Variables de entorno y secretos

- `.env.example` = plantilla **versionada** con valores de ejemplo.
- `.env` = vuestro fichero **real** con secretos (contrasenas, claves). Esta en
  `.gitignore`.
- Copiar al empezar: `copy .env.example .env`.
- **Nunca** escribir contrasenas directamente en el codigo.
- Si cambias un valor del `.env`, vuelve a levantar: `docker compose up -d`.
- En Azure, los secretos van a **Key Vault** o a los *secrets* del servicio, no al
  repo.

## 25. Git y trabajo en equipo sin liarla

- Cada persona trabaja en su **rama**: `git checkout -b feature/jose-auth`.
- Haced **commits pequenos y frecuentes**, con mensaje claro.
- Antes de subir: `git pull` para traer los cambios de los demas y evitar conflictos.
- Subir la rama y abrir un **Pull Request (PR)**; que lo revise un companero.
- **Antes de cada dia de trabajo**: `git pull`. **Al acabar**: `git push`.
- No subir ficheros enormes ni generados (`__pycache__/`, `.env`, `.pem`).
- Si aparece un **conflicto**, no entres en panico: GitHub/VS Code lo resaltan; se
  elige que linea se queda y se guarda.
- Regla de oro: **el repositorio siempre debe poder arrancar** con `docker compose up`.

## 26. Check-list para probar en local (antes de la nube)

1. `docker compose up --build` y comprobar que los 4 contenedores estan "healthy".
2. Abrir `http://localhost:8000/docs` (Swagger) y probar login con `admin`/`admin123`.
3. Subir **el mismo fichero 3 veces** -> deben aparecer **3 versiones**.
4. Descargar la version 1 y la 3 -> comprobar que el contenido es el correcto.
5. Abrir `http://localhost:8501`, probar login, subir y descargar desde la UI.
6. Ver el **LogBook** y exportarlo a **CSV** y **JSON**.
7. Probar con **un usuario sin permiso de escritura** -> debe recibir un error 403.
8. Probar en el **navegador del movil** (misma wifi, IP del PC en vez de localhost).

> Probar TODO en local primero. El 70% de los problemas se resuelven aqui y sin gastar
> credito de Azure.

## 27. HTTPS: que esperar

- En **local** se usa un certificado **autofirmado**: el navegador mostrara un aviso
  de "conexion no segura". **Es normal**; se acepta y se continua.
- En **produccion (Azure)** se usa un certificado **real gestionado**: sin avisos.
- Generar el certificado local (si usais el perfil `tls`):
  `powershell -ExecutionPolicy Bypass -File infra/nginx/gen-cert.ps1`.

## 28. Azure sin sustos (ni sustos en la factura)

- Usar **Azure for Students** (credito sin tarjeta).
- Elegir **siempre la misma region** para todos los recursos (si no, latencia y
  problemas de red).
- **Apagar o borrar** los recursos al terminar de probar (Container Apps y PostgreSQL
  cobran por tiempo encendido).
- El **Storage Account** debe tener **Blob versioning** activado.
- Guardar cadenas de conexion en **Key Vault**, no en el repo ni en capturas de
  pantalla.
- Comprobar el **coste** periodicamente en el portal.

## 29. Como usar la IA (ChatGPT/Claude/Copilot) sin pifiarla

- **Si**: generar plantillas repetitivas, explicaros un error, traducir un concepto,
  proponer tests.
- **No**: pegar **secretos**, claves o datos reales de usuarios.
- **Siempre**: entender y **revisar** lo que genera; puede inventarse funciones o
  versiones de librerias que no existen.
- **Defensa**: cada persona debe poder explicar **su parte linea a linea**. Si no la
  entiendes, no la subas.
- Las **cifras y referencias** del estado del arte hay que **verificarlas** en fuentes
  reales (la IA alucina datos).

## 30. Errores tipicos de novato (y su pista)

| Sintoma | Causa habitual | Solucion |
|---|---|---|
| `docker: command not found` | Docker Desktop cerrado | Abrir Docker Desktop |
| `connection refused` / `could not connect` | Servicio aun arrancando o host mal | Esperar; revisar nombre de servicio (`db`, no `localhost`) |
| El frontend no ve la API (CORS) | Origen no permitido | Revisar `CORS_ORIGINS` en `.env` |
| "port is already allocated" | Puerto ocupado | Cambiar el puerto de la izquierda en compose |
| Cambio el `.env` y no pasa nada | No se recreo el contenedor | `docker compose up -d` o `--build` |
| Perdi los datos | Se hizo `down -v` | Evitarlo; hacer copias/backups |
| El login devuelve 401 | Token caducado o mal enviado | Rehacer login; revisar cabecera `Authorization` |
| El upload devuelve 403 | Usuario sin permiso `write` | Revisar permisos del usuario |
| Function/version de libreria no existe | La IA la invento | Mirar documentacion oficial y fijar version |

## 31. Orden recomendado de trabajo (resumen)

1. **Contratos**: modelo de datos (ER) + contrato de la API (OpenAPI).
2. **Entorno**: `docker-compose` funcionando (Diego).
3. **Modulos aislados** en paralelo (cada uno prueba lo suyo).
4. **Integracion** (unir frontend con API real).
5. **Pruebas + seguridad**.
6. **Nube (Azure) + HTTPS**.
7. **Presentacion + demo**.

## 32. Como hacer una buena demo

- Ensayar la demo **antes**; tenerla lista por si falla la wifi (capturas/video).
- Guion minimo: login -> subir 2 veces el mismo fichero -> mostrar versiones ->
  descargar version antigua -> abrir LogBook -> exportar CSV/JSON.
- Tener a mano el **diagrama** y explicar que hace cada pieza.
- Si algo falla en directo, mantener la calma y explicar lo que **deberia** pasar
  mientras lo arreglas (o pasa a las capturas).

## 33. Consejos finales

- **No reinventar**: si el login os come mucho tiempo, se puede delegar en Entra ID o
  un proveedor (Auth0). El objetivo es el sistema completo, no reescribir la rueda.
- **Minimo privilegio**: cada usuario solo lo que necesita.
- **Backups**: hacer copias del repositorio (Git) y de la base de datos antes de los
  hitos.
- **Documentar mientras se hace**, no al final.
- **Pedir ayuda pronto**: leed la **ultima linea** del error (suele decir la causa),
  buscad en la documentacion oficial y preguntad al equipo/profesor.

## 34. Orden de lectura del resto de documentos

1. Este documento (vision completa).
2. `docs/00_plan.md` (plan y decisiones).
3. `docs/05_division_of_work.md` (tu parte).
4. `docs/04_architecture.md` (como encaja todo).
5. `docs/01`, `docs/02`, `docs/03` (contenido de la presentacion).
