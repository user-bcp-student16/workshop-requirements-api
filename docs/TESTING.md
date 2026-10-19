# Pruebas de la API

Los tests ejecutables están en [`tests/test_api.py`](../tests/test_api.py). La tabla registra las pruebas existentes y el resultado esperado/observado para cada endpoint. Se añadieron caracterizaciones para H-05/H-06 antes del refactor; los tests finales comprueban contratos y errores genéricos.

## Matriz

| Endpoint | Caso | Tipo | Resultado esperado |
|---|---|---|---|
| `GET /api/tasks` | `test_lists_seeded_tasks` | Camino feliz | `200`; lista las dos tareas iniciales de `student`. |
| `GET /api/tasks` | `test_task_listing_uses_authenticated_owner` | Seguridad / borde | `200`; con query `owner=trainer` y token de `student`, solo devuelve tareas de `student`. |
| `GET /api/tasks` | `test_task_listing_accepts_empty_owner_query` | Borde | `200`; `owner=` no cambia el propietario derivado de la identidad. |
| `GET /api/tasks` | `test_all_endpoints_reject_missing_authentication` (caso GET tasks) | Error | `401` y `{"detail":"Invalid token"}`. |
| `GET /api/tasks` | `test_task_listing_database_error_returns_500` | Error | `500` ante un fallo SQLite simulado; el cuerpo no está fijado por la ruta. |
| `GET /api/tasks` | Error `422` anunciado por OpenAPI | Pendiente | No se conoce una entrada que lo provoque: `owner` acepta string/null y no tiene restricciones. No se inventó un caso. |
| `POST /api/tasks` | `test_creates_task_and_summary` | Camino feliz | `201` al crear; el resumen posterior devuelve `200`. |
| `POST /api/tasks` | `test_task_creation_with_empty_payload_uses_defaults` | Borde | `{}` devuelve `201`; title/description vacíos, status `TODO`, priority `MEDIUM` y owner autenticado. |
| `POST /api/tasks` | `test_task_creation_stringifies_values_and_ignores_extra_fields` | Borde | `201`; convierte valores JSON a string como antes, ignora campos extra y no acepta el `owner` del cliente. |
| `POST /api/tasks` | `test_task_creation_uses_authenticated_owner` | Seguridad / borde | `201`; ignora `owner=trainer` del cuerpo y asigna `student`. |
| `POST /api/tasks` | `test_task_creation_rejects_non_object_json` | Error | `422`; el error de validación indica `dict_type`. |
| `POST /api/tasks` | `test_all_endpoints_reject_missing_authentication` (caso POST tasks) | Error | `401` con `{"detail":"Invalid token"}`. |
| `POST /api/tasks` | `test_task_creation_database_error_returns_500` | Error | `500` ante un fallo de inserción SQLite simulado. |
| `GET /api/summary` | `test_creates_task_and_summary` | Camino feliz | `200`; resume las tareas de `student` luego de crear una tarea. |
| `GET /api/summary` | `test_summary_for_owner_without_tasks` | Borde | `200`; total `0`, `byStatus` vacío y `highPriorityOpen` `0`. |
| `GET /api/summary` | `test_summary_uses_authenticated_owner` | Seguridad / borde | `200`; ignora `owner=trainer` y resume `student`. |
| `GET /api/summary` | `test_all_endpoints_reject_missing_authentication` (caso GET summary) | Error | `401` con `{"detail":"Invalid token"}`. |
| `GET /api/summary` | `test_summary_database_error_returns_500` | Error | `500` ante un fallo de consulta SQLite simulado. |
| `GET /api/summary` | Error `422` anunciado por OpenAPI | Pendiente | No se conoce un valor de `owner` que dispare validación: es string/null sin restricciones. |
| `POST /api/requirements` | `test_uploads_requirement` | Camino feliz | `201`; guarda el archivo y devuelve owner, nombre, ruta y tamaño. |
| `POST /api/requirements` | `test_uploads_empty_file_without_extension` | Borde | `201`; acepta archivo vacío sin extensión y reporta tamaño `0`. Esto caracteriza el comportamiento actual, no una garantía de seguridad. |
| `POST /api/requirements` | `test_upload_rejects_missing_file` | Error | `422`; `detail[0].loc` es `["body","file"]`. |
| `POST /api/requirements` | `test_all_endpoints_reject_missing_authentication` (caso POST requirements) | Error | `401` con `{"detail":"Invalid token"}`. |
| `POST /api/requirements` | `test_upload_write_error_returns_500` | Error | `500` al simular un error de escritura. |
| `GET /api/backend-health` | `test_backend_health_returns_backend_status_and_body` | Camino feliz | `200`; conserva status `200` y body `OK` del backend simulado. |
| `GET /api/backend-health` | `test_backend_health_preserves_non_success_backend_status` | Borde | `200` de esta API; el status remoto `503` y su body se incluyen en la respuesta. |
| `GET /api/backend-health` | `test_backend_health_reports_backend_exception` | Error remoto manejado | `200` de esta API, `status` remoto `0` y `body` genérico `Backend health request failed`. |
| `GET /api/backend-health` | `test_all_endpoints_reject_missing_authentication` (caso GET backend-health) | Error | `401` con `{"detail":"Invalid token"}`. |
| `GET /api/backend-health` | Error `422` anunciado por OpenAPI | Pendiente | La ruta no declara query ni cuerpo; no se encontró una solicitud que provoque `422`. |

## Pruebas transversales

| Test | Tipo | Resultado esperado |
|---|---|---|
| `test_app_reuses_existing_database_without_reseeding` | Caracterización de inicialización | Al abrir una base existente, conserva sus dos tareas de `student` sin sembrarlas de nuevo. |

## Código de los tests

El código fuente ejecutable de todos los casos de la matriz está centralizado en [`tests/test_api.py`](../tests/test_api.py); no se copia aquí una segunda versión que pueda desincronizarse. Ejemplos representativos:

```python
def test_task_listing_uses_authenticated_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks?owner=trainer", headers=headers("student"))

    assert response.status_code == 200
    assert [task["owner"] for task in response.json()] == ["student", "student"]
```

```python
def test_uploads_empty_file_without_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirement", b"", "application/octet-stream")},
        )

    assert response.status_code == 201
    assert response.json()["fileName"] == "requirement"
    assert response.json()["size"] == 0
    assert (upload_dir / "requirement").read_bytes() == b""
```

## Implementación H-05/H-06

- `app/database.py` concentra creación de conexión, esquema y datos iniciales.
- `app/task_service.py`, `app/requirement_service.py` y `app/backend_health_service.py` contienen reglas de aplicación; `app/task_repository.py` conserva SQL parametrizado.
- `app/schemas.py` tipa identidad, request y respuestas Pydantic; los aliases conservan las claves JSON públicas.
- `app/security.py` mantiene la autenticación legacy y responde con un error genérico. No verifica firma JWT; eso permanece pendiente en H-01.
- Los errores de red previstos del backend ya no exponen texto de excepción. H-04 sigue pendiente: mover la carga a un servicio no la vuelve segura.

## Ejecución registrada

Directorio de trabajo: raíz de `workshop-requirements-api/` (repositorio del componente).

| Comando | Código de salida | Resultado observado |
|---|---:|---|
| `\.venv\Scripts\python.exe -m coverage run --branch -m pytest tests/test_api.py -q -p no:warnings` (2026-10-19) | `0` | Suite final: `27` pruebas pasaron con cobertura de ramas. `-p no:warnings` evita imprimir warnings en esta ejecución. |
| `\.venv\Scripts\python.exe -m coverage report -m` (2026-10-19) | `0` | Cobertura total `99%`; `app/task_repository.py` `87%`; los otros ocho módulos medidos están completamente cubiertos y se omiten por `skip_covered`. |

Las advertencias observadas son deprecaciones de `anyio`/Starlette y del uso de `on_event` de FastAPI. No produjeron fallos. La suite se ejecutó contra el código actual, en entorno local, con SQLite temporal por prueba y backend de salud simulado; no requiere conexión a otro componente.

## Fallos

No hubo fallos en la última suite ejecutada. Los errores SQLite y de almacenamiento de la tabla son inyectados por tests para verificar los status `500`; no son fallos observados en una base de datos o disco real.

## Pendientes y bugs observados

- **Autenticación e IDOR:** los tests de `owner` verifican que el parámetro se ignora, pero el helper de pruebas puede crear tokens legacy para cualquier username. Como el token Base64 no tiene firma, no prueban que un cliente no pueda suplantar el username de otro usuario. La garantía completa de no leer tareas ajenas queda pendiente de corregir y probar autenticación real.
- **Validación `422` en GET:** OpenAPI anuncia `422` para `GET /api/tasks`, `GET /api/summary` y `GET /api/backend-health`, pero el código actual no presenta una restricción de request que permita provocar ese error. No hay test de error de runtime para esos casos; queda pendiente aclarar o ajustar el contrato.
- **Carga de archivos:** el test de archivo sin extensión documenta que hoy se acepta. El código usa el filename directamente, lee todo el contenido en memoria y no limita tamaño ni extensión. No se añadieron pruebas que normalicen ese comportamiento como una protección; path traversal, límites de tamaño y extensiones permitidas siguen sin resolver.
- **JWT:** no hay tests de firma, issuer, audience o expiración para JWT real; la implementación sigue usando el token legacy.
- **Errores internos:** las pruebas verifican status `500`, no un cuerpo, porque el código no define uno estable. Ese formato sigue abierto.

## Pruebas propuestas

- Cuando se defina el contrato de JWT, agregar casos de firma válida/alterada, issuer y audience incorrectos, expiración, ausencia de token y suplantación de username; no usar credenciales reales.
- Cuando se acuerde el contrato de archivos, agregar pruebas de rechazo para path traversal, extensión no permitida y tamaño sobre el límite. No asumir esos límites antes de implementarlos.
- Resolver si los `422` de los GET forman parte del contrato y solo entonces añadir una prueba que reproduzca una entrada inválida real.