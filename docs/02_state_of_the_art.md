# 02 - State of the art

## Research (metodos y fuentes)

- **Fuentes primarias**: documentacion oficial de Azure (Blob Storage, Entra ID,
  Container Apps), AWS (S3 versioning), Google Cloud Storage.
- **Productos de referencia**: Google Drive, Dropbox, Microsoft OneDrive/SharePoint,
  Nextcloud (open source, autoalojado).
- **Estandares y seguridad**: OWASP Top 10, RFC 7519 (JWT), TLS/HTTPS (RFC 8446).
- **Literatura**: articulos sobre almacenamiento de objetos y sincronizacion de
  ficheros (bases de datos + almacenamiento de objetos, deduplicacion, versionado).
- **Metodo**: analisis funcional (que capacidades ofrece cada producto) + analisis
  tecnico (modelo de almacenamiento, versionado, permisos, seguridad).

> IMPORTANTE: verificar cifras/precios/versiones en las fuentes oficiales antes de
> presentarlas. No incluir datos inventados por IA sin comprobarlos.

## Related work (soluciones existentes)

| Producto | Ventajas | Desventajas |
|---|---|---|
| **Google Drive** | Muy accesible desde cualquier dispositivo; edicion colaborativa; versionado de archivos. | Caja negra (no controlas infraestructura); API compleja; limites de cuota; autenticacion delegada en Google. |
| **Dropbox** | Excelente sincronizacion; historial de versiones; muy fiable. | De pago para funciones clave; poca personalizacion; dependencia total del proveedor. |
| **Microsoft OneDrive/SharePoint** | Integracion con Office y Entra ID; versionado y permisos granulares. | Ecosistema muy corporativo; configuracion compleja; coste. |
| **Nextcloud (open source)** | Autoalojable; control total; versionado y control de acceso; extensible. | Hay que gestionar servidores, seguridad y escalado. |

## Comparativa detallada de las 3 soluciones mas cercanas

Criterios alineados con el enunciado: HTTPS, almacenamiento cloud, auth/permisos,
versionado, LogBook/auditoria, acceso multi-dispositivo, coste.

| Criterio | Google Drive | Dropbox | OneDrive/SharePoint |
|---|---|---|---|
| Transferencia HTTPS | Si | Si | Si |
| Almacenamiento cloud | Si | Si | Si |
| Autenticacion | Cuenta Google (OAuth2) | Cuenta Dropbox | Cuenta Microsoft / Entra ID |
| Permisos granulares | Comparticion por archivo/carpeta | Comparticion por archivo/carpeta | Permisos por rol muy detallados |
| Control de versiones | Si (historial) | Si (historial) | Si (historial) |
| LogBook / auditoria | Registro de actividad (limitado) | Eventos (planes avanzados) | Auditoria avanzada (corporativo) |
| Multi-dispositivo | Web + apps nativas | Web + apps nativas | Web + apps nativas |
| Codigo abierto | No | No | No |

### Conclusion de la comparativa

Los tres productos comerciales **ya resuelven** el problema a gran escala, pero son
cajas negras, dependientes del proveedor, y no exponen su LogBook ni su modelo de
versionado de forma que el usuario pueda adaptarlo. Nuestro proyecto **construye** ese
sistema encima de infraestructura cloud (Azure), con **control total** de la
autenticacion, los permisos, el versionado (fecha, tamano, version) y el LogBook
exportable (CSV/JSON), que es exactamente lo que pide el enunciado. Nextcloud es la
referencia mas cercana en filosofía (control propio), pero exige gestion de
servidores, algo que aqui delegamos en un cloud gestionado.
