# Resultado de pruebas

## Alcance

Ejecución local de `tests/test_api.py` para H-02, primero caracterizando el comportamiento previo y luego comprobando la corrección. Los comandos se ejecutaron con el Python del entorno virtual del repositorio. No se modificó ni probó la implementación JWT de H-01, porque faltan los parámetros confirmados por el emisor.

## Ejecuciones

| Etapa | Comando | Resultado |
|---|---|---|
| Caracterización del comportamiento anterior | `\.venv\Scripts\python.exe -m pytest tests/test_api.py -k characterizes` | **3 pasaron** antes de cambiar la implementación. Confirmaron que `student` podía listar el `owner=trainer`, obtener su resumen y crear una tarea como `trainer`. Estas aserciones temporales se reemplazaron por las regresiones seguras. |
| Regresión segura antes de la corrección | `\.venv\Scripts\python.exe -m pytest tests/test_api.py -k 'authenticated_owner'` | **3 fallaron**, como se esperaba: listado y resumen devolvieron datos de `trainer`, y la creación asignó `trainer` pese a autenticar como `student`. |
| Regresión segura después de la corrección | `\.venv\Scripts\python.exe -m pytest tests/test_api.py -k 'authenticated_owner'` | **3 pasaron**. Las tres operaciones utilizaron el usuario de la identidad recibida, ignorando el `owner` enviado por el cliente. |
| Suite completa con cobertura de ramas | `\.venv\Scripts\python.exe -m coverage run --branch -m pytest tests/test_api.py` | **7 pasaron**, 17 advertencias de deprecación. |
| Informe de cobertura | `\.venv\Scripts\python.exe -m coverage report -m app/main.py app/task_service.py app/task_repository.py` | **91% total** en las unidades reportadas: `app/main.py` 89%, `app/task_repository.py` 87% y `app/task_service.py` con cobertura completa (omitido por `skip_covered`). |

Las advertencias observadas corresponden a la API de `anyio` usada por Starlette y al uso de `on_event` de FastAPI. No provocaron fallos.

## Límites

- Los resultados de caracterización y fallos previos son ejecuciones intencionales anteriores a la corrección, no fallos de la suite final.
- H-01 sigue pendiente: no se ejecutaron pruebas de JWT válido, firma, `issuer`, `audience` o expiración con el contrato real del emisor.
- No se ejecutaron escáneres de seguridad ni pruebas de explotación.