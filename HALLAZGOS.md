# Hallazgos de la API

## Alcance

Inventario basado en el código y las dependencias de este repositorio, tomando como guía los casos enumerados en `RETO.md`. H-03, H-05 y H-06 están resueltos según el código y las pruebas actuales. H-02 sigue pendiente end-to-end mientras H-01 permita suplantar la identidad; H-04, H-07 y H-08 también siguen pendientes. Los impactos que dependen del entorno se identifican como riesgos potenciales.

## Hallazgos

`Pendiente` significa que todavía no se ha incorporado y verificado una corrección para el hallazgo. En H-07 también falta verificar los CVE aplicables.

| ID | Estado | Área | Hecho observado | Riesgo potencial / evaluación |
|---|---|---|---|
| H-01 | Pendiente | Autenticación | `legacy_identity` decodifica un token Base64 y compara un campo con un secreto constante. No valida firma criptográfica, issuer ni audience. Evidencia: [`app/security.py`](app/security.py). | Base64 no aporta integridad; sigue siendo posible falsificar la identidad si se construye un token aceptado. No se confirmó el contrato JWT del emisor. |
| H-02 | Pendiente | Autorización | El servicio toma el propietario de la identidad tipada e ignora `owner` de query/cuerpo, pero esa identidad sigue derivándose del token legacy sin firma. Evidencia: [`app/security.py`](app/security.py), [`app/task_service.py`](app/task_service.py). | La autorización por parámetro quedó corregida; el cierre end-to-end sigue pendiente hasta que H-01 entregue una identidad criptográficamente verificada. Las pruebas actuales no demuestran resistencia a falsificar el username. |
| H-03 | Resuelto | SQL | Las consultas de tareas ya no concatenan valores del cliente. Los filtros de propietario, campos de inserción y lectura por ID usan placeholders SQLite. Evidencia: [`app/task_repository.py`](app/task_repository.py). | Resolución: `list_tasks_by_owner`, `insert_task` y `get_summary_tasks` pasan los valores mediante parámetros separados. Las rutas de tareas delegan estas operaciones al repositorio. No se evaluaron otras consultas que solo contienen SQL constante de esquema o datos semilla. |
| H-04 | Pendiente | Archivos | El servicio aún construye el destino directamente desde `file.filename`, lee el archivo completo y no valida nombre, extensión ni tamaño. Evidencia: [`app/requirement_service.py`](app/requirement_service.py). | La extracción de capa no corrige path traversal ni consumo de memoria. Las pruebas solo caracterizan el comportamiento actual; H-04 requiere controles de archivo dedicados. |
| H-05 | Resuelto | Arquitectura | `app/main.py` ahora ensambla la aplicación y adapta HTTP; inicialización de DB, autenticación, reglas de tareas, carga y consulta de salud se delegan a módulos separados. Evidencia: [`app/main.py`](app/main.py), [`app/database.py`](app/database.py), [`app/security.py`](app/security.py), [`app/task_service.py`](app/task_service.py), [`app/task_repository.py`](app/task_repository.py), [`app/requirement_service.py`](app/requirement_service.py), [`app/backend_health_service.py`](app/backend_health_service.py). | Resolución: separación de responsabilidades ruta/servicio/repositorio; las pruebas de integración de `tests/test_api.py` caracterizan inicialización, tareas, carga y backend-health con dependencias externas simuladas. La lógica de protección de archivos sigue pendiente bajo H-04, no se considera resuelta por esta extracción. |
| H-06 | Resuelto | Calidad | La identidad, el request de creación y las respuestas exitosas usan modelos Pydantic; los aliases mantienen las claves JSON legacy. Los errores de autenticación y backend ya no exponen texto de excepción; el resumen usa constantes, `Counter` y condiciones combinadas. Evidencia: [`app/schemas.py`](app/schemas.py), [`app/security.py`](app/security.py), [`app/backend_health_service.py`](app/backend_health_service.py), [`app/task_service.py`](app/task_service.py). | Resolución: se conservan defaults, coerción a string y el error `dict_type` mediante un `RootModel` del objeto JSON, con propiedades tipadas. Tests de coerción, alias, error genérico y respuesta remota: [`tests/test_api.py`](tests/test_api.py). La autenticación criptográfica sigue pendiente como H-01; H-06 no la declara corregida. |
| H-07 | Pendiente | SCA | `requirements.txt` fija `urllib3==2.5.0` y `python-multipart==0.0.21`. Evidencia: [`requirements.txt`](requirements.txt#L4), [`requirements.txt`](requirements.txt#L5). | Las versiones coinciden con las señaladas por `RETO.md`, pero este repositorio no documenta aquí CVE concretos ni una fuente de advisories. No se verificó en una base de vulnerabilidades qué CVE aplica ni qué versión corregida debe adoptarse. |
| H-08 | Pendiente | Contrato OpenAPI | Swagger declara el parámetro `Authorization` como opcional y no lista `401`, aunque la implementación exige identidad y devuelve `401` si el token no es válido. Las respuestas de éxito ahora usan esquemas Pydantic tipados. Evidencia: OpenAPI servido en `http://localhost:8000/openapi.json`; [`app/main.py`](app/main.py), [`app/security.py`](app/security.py). | `docs/ENDPOINTS.md` documenta los campos y la discrepancia, pero el esquema OpenAPI generado aún no refleja el requisito de autenticación ni el estado `401`. H-08 sigue pendiente. |

## Rutas observadas

El OpenAPI servido por Swagger (OAS 3.1.0) y el código definen las mismas cinco rutas:

| Operación | Parámetros / solicitud | Respuestas documentadas |
|---|---|---|
| `GET /api/tasks` | Query `owner` opcional | `200`: arreglo de `TaskResponse`; `422`: `HTTPValidationError` |
| `POST /api/tasks` | Cuerpo JSON requerido como objeto | `201`: `TaskResponse`; `422`: `HTTPValidationError` |
| `GET /api/summary` | Query `owner` opcional | `200`: `TaskSummaryResponse`; `422`: `HTTPValidationError` |
| `POST /api/requirements` | `multipart/form-data` requerido con campo binario `file` | `201`: `RequirementUploadResponse`; `422`: `HTTPValidationError` |
| `GET /api/backend-health` | Sin parámetros de operación | `200`: `BackendHealthResponse`; `422`: `HTTPValidationError` |

Swagger añade el parámetro `Authorization` opcional a las cinco operaciones. El código exige que su valor produzca una identidad válida. Las respuestas listadas arriba son las que declara OpenAPI; la ausencia de `401` se registra en H-08. `docs/ENDPOINTS.md` documenta los campos observados en los modelos y las preguntas abiertas.

## Evidencia faltante y límites

- `docs/ENDPOINTS.md` documenta los campos observados en el código. El OpenAPI generado por FastAPI aún publica esquemas genéricos y no declara `401`; la discrepancia de autenticación de H-08 continúa pendiente.
- No existe `HALLAZGOS.md` previo; este archivo crea el inventario inicial a partir de `RETO.md` y el código disponible.
- No se consultaron advisories externos ni se determinaron CVE o versiones corregidas.
- Para H-05/H-06, la suite actual documentada en `docs/TESTING.md` pasa 27 pruebas y reporta 99% de cobertura total de `app`; `app/task_repository.py` tiene 87%. Las pruebas de autorización de H-02 no validan la autenticidad del token. No se ejecutaron escáneres ni pruebas de explotación. Los riesgos restantes son inferencias del flujo de código, no resultados de explotación.
- La lista cubre los casos sembrados en `RETO.md`; no representa una auditoría exhaustiva de seguridad.

## Siguiente paso

Confirmar el contrato de autenticación con el emisor para cerrar H-01 y H-02; resolver H-04 con normalización y límites de archivo; validar H-07 contra una fuente oficial de advisories; y decidir si Swagger documenta el requisito real de autenticación y el `401`.