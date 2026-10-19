# Plan de corrección: H-01, H-02, H-05 y H-06
# Plan Aprobado por Luis Chavez fecha:19/10/26

> La aprobación registrada cubre la propuesta original para H-01 y H-02. Una solicitud posterior autorizó explícitamente implementar H-05 y H-06; ambos cambios están implementados y verificados abajo.

## Base y límites

La propuesta original cubre H-01 y H-02. La ampliación añadió H-05 y H-06, que estaban `Pendiente` en `HALLAZGOS.md`; H-05/H-06 se implementaron después de la autorización explícita del usuario. H-01/H-02 siguen pendientes por la dependencia de autenticación JWT.

La implementación conservó rutas, códigos de éxito y claves de respuesta documentadas en `docs/ENDPOINTS.md`. El OpenAPI generado sigue marcando `Authorization` como opcional y no lista `401`, mientras la implementación exige una identidad válida. Los mensajes de error cambiaron a genéricos; la estructura/status de respuesta se conserva. Las diferencias documentales aún abiertas deben resolverse sin inventar contratos.

## Contrato que se preservará

- Mantener `GET /api/tasks`, `POST /api/tasks`, `GET /api/summary`, `POST /api/requirements` y `GET /api/backend-health`, con sus métodos, rutas y formatos de solicitud y respuesta actuales.
- Mantener los estados de éxito observados: `200` para las consultas y `201` para las creaciones/cargas. No cambiar nombres ni estructura de campos de las respuestas.
- Mantener el header `Authorization: Bearer ...`. El reemplazo del token Base64 por JWT implica una migración de credenciales del emisor/cliente; no se debe desplegar sin coordinarla.
- Mantener el parámetro opcional `owner` y la forma actual del cuerpo de creación. Para H-02, esos valores no concederán acceso ni definirán el propietario; las operaciones se limitarán a la identidad autenticada.

## H-01: autenticación sin firma verificable

**Hallazgo de origen.** H-01 de `HALLAZGOS.md` («Autenticación»): `legacy_identity` decodifica Base64 y compara un campo con un secreto fijo; no verifica firma criptográfica, emisor ni audiencia.

**Problema.** Base64 no autentica ni protege la integridad del contenido. Un token aceptado de esta forma no acredita que lo haya emitido un emisor confiable.

**Cambio propuesto.** Sustituir la validación manual por una biblioteca mantenida de verificación JWT, inicialmente PyJWT si la coordinación confirma que cubre el algoritmo y la distribución de claves del emisor. Verificar firma usando una lista de algoritmos permitidos fijada por configuración confiable, además de `iss`, `aud` y `exp`; derivar la identidad de claims acordados con el emisor. Rechazar tokens inválidos con `401` y mensaje genérico, sin devolver excepciones crudas. Extraer la verificación a una función de seguridad con una sola responsabilidad y dejar en `app/main.py` únicamente su integración como dependencia.

No hay una biblioteca JWT declarada actualmente en `requirements.txt`, por lo que la dependencia se justificaría para evitar implementar criptografía propia. Añadirla solo después de confirmar algoritmo y mecanismo de claves; fijar una versión mantenida y revisar advisories. No guardar secretos reales en el repositorio ni en pruebas.

**Coordinación externa necesaria.** Sin leer otros componentes, confirmar con el emisor: issuer exacto, audience, algoritmo admitido, clave pública/JWKS o mecanismo de claves, claim que identifica al usuario y claim de rol si aplica, rotación de claves y procedimiento de migración desde el token actual. Configurar valores por entorno/gestor de secretos, nunca aceptar algoritmo o claves elegidos por el propio token.

**Archivos previstos.** `app/main.py` (conectar la dependencia y tipar la identidad interna), `app/security.py` (nuevo verificador), `requirements.txt` (solo si se confirma la dependencia) y `tests/test_api.py`. `README.md` podría documentar nombres de configuración no secretos una vez acordados.

**Pruebas de caracterización antes de tocar la implementación.** En `tests/test_api.py`, primero fijar los estados de éxito y campos actuales de las rutas protegidas que ya tienen cobertura; agregar cobertura de contrato para las rutas restantes, simulando la llamada externa de backend-health. Luego agregar pruebas con una clave efímera de test y claims no productivos: JWT válido conserva las respuestas `200`/`201`; firma alterada, token malformado, `iss`/`aud` incorrectos y expiración pasada reciben `401` genérico. Cubrir también ausencia de credencial y que ninguna respuesta revele datos internos. Las pruebas negativas de JWT se esperan rojas hasta que se implemente el verificador; no se deben convertir en tests del formato inseguro anterior.

## H-02: autorización controlada por `owner` del cliente

**Hallazgo de origen.** H-02 de `HALLAZGOS.md` («Autorización»): `GET /api/tasks` y `GET /api/summary` usan el `owner` de query si se envía; `POST /api/tasks` permite elegir `owner` en el cuerpo.

**Problema.** La autenticación por sí sola no impide consultar ni crear tareas bajo la identidad de otro usuario. No se observa una regla de rol documentada que autorice acceso cruzado.

**Cambio propuesto.** Aplicar la convención de `docs/GOOD_PRACTICES.md`: usar siempre el `username` de la identidad ya verificada para listar, resumir y crear tareas. Conservar el parámetro opcional `owner` y el campo de cuerpo por compatibilidad estructural, pero no usarlos para seleccionar ni asignar propietario. La respuesta de creación debe devolver como `owner` la identidad autenticada. Si se requiere que un rol como trainer consulte otros propietarios, definir primero una política de roles explícita; no inferirla del valor enviado por el cliente.

Para seguir la separación ruta → servicio → repositorio indicada en `docs/GOOD_PRACTICES.md`, delegar la selección de propietario/reglas a `app/task_service.py` y las consultas e inserciones afectadas a `app/task_repository.py`. El repositorio recibirá el propietario autorizado como argumento y parametrizará sus valores SQL; la ruta no construirá SQL. Mantener cada función enfocada, extraer lógica común sin duplicarla y usar constantes con nombre para cualquier valor fijo necesario. Este cambio parametriza las consultas tocadas por H-02; no declarar cerrado H-03 sin actualizar y verificar su estado por separado.

**Archivos previstos.** `app/main.py` (delegación sin cambiar rutas ni parámetros públicos), `app/task_service.py` (nuevo), `app/task_repository.py` (nuevo) y `tests/test_api.py`.

**Pruebas de caracterización antes de tocar la implementación.** Añadir en `tests/test_api.py` pruebas con dos identidades distintas: al solicitar tareas o resumen con `owner` ajeno, el usuario recibe solo sus propios datos y el resumen identifica su propio usuario; al crear una tarea enviando un `owner` ajeno, la operación conserva `201` y la respuesta atribuye la tarea al usuario autenticado. Mantener aserciones de las claves y formatos actuales. Estas pruebas deben demostrar el acceso cruzado actual antes del cambio y quedar como pruebas de regresión que pasan con la política corregida. Ejecutarlas con datos SQLite aislados por prueba.

## H-05: responsabilidades concentradas en `app/main.py`

**Hallazgo de origen.** H-05 de `HALLAZGOS.md` (`Pendiente`): la lógica de tareas se separó parcialmente, pero `app/main.py` aún crea la conexión/esquema/datos iniciales y contiene autenticación, carga de archivos y endpoints, incluida lógica de backend-health.

**Problema.** La composición de la aplicación, persistencia, reglas de carga y llamada HTTP externa siguen mezcladas con las rutas. Esto deja más de una responsabilidad por función/módulo y dificulta probar las capas sin levantar toda la API.

**Cambio propuesto.** Completar la separación ruta → servicio → repositorio indicada por `docs/GOOD_PRACTICES.md`: mantener `app/main.py` como ensamblaje de FastAPI y adaptador HTTP; extraer la apertura/inicialización SQLite a `app/database.py`; mantener SQL en `app/task_repository.py`; y delegar carga de requerimientos y consulta al backend en servicios separados (`app/requirement_service.py` y `app/backend_health_service.py`). Reutilizar `app/task_service.py` para las reglas de tareas existentes. La ruta valida/extrae inputs, llama a un servicio y devuelve su resultado; no crea SQL ni implementa persistencia o llamadas de red. Esta separación no debe adelantarse a H-04: hasta resolver ese hallazgo, el servicio de archivos conservará el comportamiento documentado, no se considerará seguro por moverlo de módulo.

**Archivos previstos.** `app/main.py`; nuevos `app/database.py`, `app/requirement_service.py` y `app/backend_health_service.py`; `app/task_service.py` y `app/task_repository.py` para ajustar interfaces si hace falta; `tests/test_api.py` y pruebas unitarias nuevas solo si los helpers de test existentes no bastan. No se cambiarán métodos, rutas, códigos de éxito ni nombres/tipos de campos de respuesta.

**Pruebas de caracterización antes de separar módulos.** En `tests/test_api.py`, fijar las respuestas actuales completas (claves y tipos) y códigos `200`/`201` de tareas, resumen y carga; probar inicialización/semillas con una base aislada; y simular el backend para sus respuestas HTTP `200`, no exitosas y excepción traducida a `status: 0`. Mantener las pruebas de autorización existentes. Ejecutarlas antes del movimiento para confirmar el baseline y después para demostrar que la extracción no cambia el contrato. Añadir tests de unidad para cada servicio/repository solo tras establecer la caracterización de integración.

**Clean Code y límites.** Cada servicio tendrá una responsabilidad; el repositorio conservará únicamente SQL parametrizado; la capa de rutas no tendrá SQL, escritura de archivos ni `PoolManager`. Evitar copiar lógica o serializadores y no añadir configuraciones/constantes mágicas sin nombre. La extracción de archivos no corrige por sí sola H-04, H-01 ni H-07.

## H-06: tipos y manejo de errores/calidad

**Hallazgo de origen.** H-06 de `HALLAZGOS.md` (`Pendiente`): request, identidad y respuestas todavía usan `dict`; hay capturas amplias de `Exception`, y el manejo de errores de backend expone el texto de la excepción. Parte del anidamiento del resumen ya se simplificó en `app/task_service.py`.

**Problema.** El contrato de campos no queda validado ni expresado en tipos; los errores inesperados se confunden con errores de credenciales o del servicio remoto, y devolver texto de excepción puede revelar detalles internos. También se corre el riesgo de cambiar silenciosamente las coerciones/defaults actuales al introducir modelos.

**Cambio propuesto.** Añadir modelos Pydantic de request/response para tarea, resumen, carga e identidad, con aliases `createdAt`, `byStatus` y `highPriorityOpen` para preservar exactamente las claves JSON de `docs/ENDPOINTS.md`. Definir explícitamente los defaults actuales del cuerpo de `POST /api/tasks`, la conversión actual de valores a string y el tratamiento de propiedades adicionales antes de endurecer validación; cualquier cambio observable necesita decisión de contrato y actualización coordinada de `docs/ENDPOINTS.md`. Compartir el modelo/contrato de identidad con la implementación H-01, sin crear dos representaciones distintas del mismo token. Sustituir capturas amplias por excepciones esperadas: H-01 define el error genérico `401`; el manejo de backend-health solo captura fallos de red previstos y conserva la forma `{requestedBy, status, body}`, sin devolver `str(exception)`. Mantener retornos anticipados, constantes con nombre y helpers reutilizables; no reintroducir anidamiento o duplicación.

**Archivos previstos.** Nuevo `app/schemas.py`; `app/main.py` (anotar modelos de entrada/salida en rutas); `app/task_service.py` y `app/task_repository.py` para usar tipos explícitos; `app/backend_health_service.py` según H-05; `app/security.py`/`app/main.py` coordinados con H-01; `docs/ENDPOINTS.md` solo si se acuerda un cambio contractual; y `tests/test_api.py`.

**Pruebas de caracterización antes de endurecer tipos/manejo de errores.** Capturar primero los payloads y respuestas actuales para cada endpoint: campos exactos, aliases, defaults, coerción de title/description/status/priority, campos extras ignorados, status codes y respuesta de error de token. Para backend-health, fijar que fallos de red mantienen status HTTP `200` de la API y `status: 0` en el JSON, además de comprobar que la respuesta no exponga detalles internos tras la corrección. Las pruebas que describan un comportamiento actual indeseado deben separarse como caracterización temporal y convertirse en regresiones con expectativa segura solo cuando el contrato permita el cambio. Añadir casos de validación Pydantic de borde después de fijar el baseline. No probar respuestas `422` de GET mientras no exista una entrada inválida definida por el contrato.

**Cobertura y Clean Code.** Ejecutar tests de endpoints y unidades de servicios nuevos; mantener cobertura del código modificado de 85% o superior. Evitar `dict[str, Any]` en los límites HTTP, evitar `except Exception` salvo que exista una frontera documentada con respuesta genérica, y centralizar conversiones/defaults/serialización en funciones pequeñas con nombres que expresen propósito.

## Orden y verificación posterior

1. Confirmar con el emisor los parámetros JWT y resolver la discrepancia documental del header/respuesta `401` sin alterar rutas ni formatos de éxito.
2. Añadir primero las pruebas de caracterización indicadas para ambos hallazgos y registrar qué fallan por los defectos actuales.
3. Implementar H-01 y H-02 en sus módulos respectivos, sin incorporar valores de producción; mantener la meta de cobertura de al menos 85% para el código modificado.
4. H-05/H-06: caracterización añadida antes del refactor; capas y modelos implementados. Resultado registrado: 27 pruebas pasan y cobertura total medida de `app` es 99% (`task_repository.py`: 87%).
5. Ejecutar las pruebas específicas y la suite completa al modificar los hallazgos aún pendientes; medir cobertura del código modificado (meta mínima 85%) y comparar rutas, requests y responses con `docs/ENDPOINTS.md`. Mantener registrados como preguntas abiertas los errores sin trigger/cuerpo definido.

La verificación de `iss`, `aud`, algoritmo, claims y rotación de H-01 depende de coordinación externa. H-05/H-06 están implementados; H-05/H-06 no resuelven la autenticación débil de H-01 ni la carga insegura de H-04.