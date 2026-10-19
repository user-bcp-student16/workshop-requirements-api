# Hallazgos de la API

## Alcance

Inventario basado en el código y las dependencias de este repositorio, tomando como guía los casos enumerados en `RETO.md`. La política de H-02 se cambió y sus pruebas pasan, pero su cierre end-to-end está pendiente mientras H-01 permita suplantar la identidad. Los demás hallazgos no se modificaron. Los impactos que dependen del entorno se identifican como riesgos potenciales.

## Hallazgos

`Pendiente` significa que todavía no se ha incorporado y verificado una corrección para el hallazgo. En H-07 también falta verificar los CVE aplicables.

| ID | Estado | Área | Hecho observado | Riesgo potencial / evaluación |
|---|---|---|---|
| H-01 | Pendiente | Autenticación | `legacy_identity` decodifica un token Base64 y compara un campo con un secreto constante en el código. Comprueba el formato y una fecha de expiración, pero no valida firma criptográfica, emisor ni audiencia. El valor del secreto se omite deliberadamente. Evidencia: [`app/main.py`](app/main.py#L14), [`app/main.py`](app/main.py#L20), [`app/main.py`](app/main.py#L22). | Base64 no aporta integridad. Si un cliente puede construir un token que satisfaga la comparación con el secreto del código, puede suplantar la identidad indicada en el token. No se evaluó un esquema de reemplazo ni la integración con el emisor externo. |
| H-02 | Pendiente | Autorización | El cambio elimina `owner` de query/cuerpo como fuente de autorización: el servicio usa `identity["username"]`. Sin embargo, `legacy_identity` obtiene ese username de un token Base64 y solo compara un secreto constante; no verifica firma. Evidencia: [`app/main.py`](app/main.py#L16), [`app/main.py`](app/main.py#L19), [`app/main.py`](app/main.py#L22), [`app/task_service.py`](app/task_service.py#L25), [`app/task_service.py`](app/task_service.py#L33), [`app/task_service.py`](app/task_service.py#L49). | El acceso cruzado por parámetro `owner` se corrigió, pero no queda cerrado end-to-end: un cliente que construya un token aceptado con el username de otra persona obtiene esa identidad y puede consultar sus datos. H-02 permanece pendiente hasta que H-01 provea una identidad criptográficamente verificada. Las pruebas actuales verifican el uso de identidad una vez aceptada, no que esta no pueda falsificarse: [`tests/test_api.py`](tests/test_api.py#L41), [`tests/test_api.py`](tests/test_api.py#L50), [`tests/test_api.py`](tests/test_api.py#L60). |
| H-03 | Pendiente | SQL | Los filtros de propietario y los campos de inserción se concatenan para construir SQL. Evidencia: [`app/main.py`](app/main.py#L70), [`app/main.py`](app/main.py#L84), [`app/main.py`](app/main.py#L93). | La concatenación permite que entradas con sintaxis SQL alteren la consulta. No se enviaron payloads ni se probaron efectos en la base de datos. |
| H-04 | Pendiente | Archivos | La ruta construye el destino directamente a partir de `file.filename`, lee el archivo completo en memoria y escribe esos bytes sin comprobar nombre, extensión o tamaño. Evidencia: [`app/main.py`](app/main.py#L108), [`app/main.py`](app/main.py#L109), [`app/main.py`](app/main.py#L110), [`app/main.py`](app/main.py#L111). | Según la plataforma y el nombre aceptado, una ruta manipulada podría escribir fuera del directorio previsto; la lectura completa también puede consumir memoria proporcional al tamaño recibido. No se probó el comportamiento específico del sistema de archivos. |
| H-05 | Pendiente | Arquitectura | La creación de la aplicación, conexión y esquema SQLite, datos iniciales, serialización y rutas viven en `app/main.py`; las rutas ejecutan consultas directamente. Evidencia: [`app/main.py`](app/main.py#L29), [`app/main.py`](app/main.py#L38), [`app/main.py`](app/main.py#L56), [`app/main.py`](app/main.py#L67). | La concentración de responsabilidades dificulta aislar y probar reglas, persistencia y transporte. La separación en capas requeriría cambios; no se realizó ninguno en esta revisión. |
| H-06 | Pendiente | Calidad | Las rutas aceptan cuerpos y representan identidades/respuestas con `dict`; hay capturas amplias de `Exception` y condiciones anidadas en el resumen. Evidencia: [`app/main.py`](app/main.py#L25), [`app/main.py`](app/main.py#L78), [`app/main.py`](app/main.py#L91), [`app/main.py`](app/main.py#L99), [`app/main.py`](app/main.py#L120). | Los tipos de entrada/salida quedan poco restringidos, las excepciones pueden ocultar errores concretos y la lógica anidada es más difícil de mantener. No se evaluaron todos los casos de duplicación mencionados en `RETO.md`. |
| H-07 | Pendiente | SCA | `requirements.txt` fija `urllib3==2.5.0` y `python-multipart==0.0.21`. Evidencia: [`requirements.txt`](requirements.txt#L4), [`requirements.txt`](requirements.txt#L5). | Las versiones coinciden con las señaladas por `RETO.md`, pero este repositorio no documenta aquí CVE concretos ni una fuente de advisories. No se verificó en una base de vulnerabilidades qué CVE aplica ni qué versión corregida debe adoptarse. |
| H-08 | Pendiente | Contrato OpenAPI | Swagger declara el parámetro `Authorization` como opcional con valor predeterminado vacío y no lista `401` en las respuestas. En el código, todas las rutas dependen de `legacy_identity`, que responde `401` cuando el token no es válido, incluido el caso vacío. Evidencia: OpenAPI servido en `http://localhost:8000/openapi.json`; [`app/main.py`](app/main.py#L25), [`app/main.py`](app/main.py#L67). | La documentación no refleja el requisito efectivo de autenticación ni uno de sus estados de respuesta. Los esquemas de respuesta OpenAPI son objetos genéricos y no especifican sus campos; por ello, no permiten verificar todos los formatos con detalle. |

## Rutas observadas

El OpenAPI servido por Swagger (OAS 3.1.0) y el código definen las mismas cinco rutas:

| Operación | Parámetros / solicitud | Respuestas documentadas |
|---|---|---|
| `GET /api/tasks` | Query `owner` opcional | `200`: arreglo de objetos genéricos; `422`: error de validación |
| `POST /api/tasks` | Cuerpo JSON requerido, objeto genérico | `201`: objeto genérico; `422`: error de validación |
| `GET /api/summary` | Query `owner` opcional | `200`: objeto genérico; `422`: error de validación |
| `POST /api/requirements` | `multipart/form-data` requerido con campo binario `file` | `201`: objeto genérico; `422`: error de validación |
| `GET /api/backend-health` | Sin parámetros de operación | `200`: objeto genérico; `422`: error de validación |

Swagger añade el parámetro `Authorization` opcional a las cinco operaciones. El código exige que su valor produzca una identidad válida. Las respuestas listadas arriba son las que declara OpenAPI; la ausencia de `401` se registra en H-08. Los contratos ahora contrastados son los expuestos por el servicio local; no se encontró el archivo fuente `docs/ENDPOINTS.md`.

## Evidencia faltante y límites

- No existe `docs/ENDPOINTS.md`, aunque `RETO.md` lo identifica como fuente de contratos. Se pudo consultar el OpenAPI del servicio local; aun así, sus esquemas de respuestas genéricos no permiten verificar los campos exactos de cada formato.
- No existe `HALLAZGOS.md` previo; este archivo crea el inventario inicial a partir de `RETO.md` y el código disponible.
- No se consultaron advisories externos ni se determinaron CVE o versiones corregidas.
- Para el cambio de política de H-02, las siete pruebas de `tests/test_api.py` pasan y la cobertura informada para las unidades de aplicación tocadas es 91%. Esto no valida la autenticidad del token. No se ejecutaron escáneres, cargas de archivos ni pruebas de explotación. Los riesgos restantes son inferencias del flujo de código, no resultados de explotación.
- La lista cubre los casos sembrados en `RETO.md`; no representa una auditoría exhaustiva de seguridad.

## Siguiente paso

Recuperar el contrato esperado de `docs/ENDPOINTS.md` y validar los CVE contra una fuente oficial de advisories antes de planificar cambios. Después, añadir pruebas de caracterización para los contratos confirmados y priorizar las correcciones sin alterar las rutas ni sus formatos.