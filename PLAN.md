# Plan de corrección: H-01 y H-02
# Plan Aprobado por Luis Chavez fecha:19/10/26
## Base y límites

Este plan toma H-01 por la prioridad alta indicada en la solicitud y H-02 por su alcance acotado. `HALLAZGOS.md` no contiene una columna de estado ni marca explícitamente hallazgos como «Pendiente»; por tanto, la selección proviene de la solicitud, no de un estado comprobado en ese archivo.

No se modificará código en esta etapa. El archivo `docs/ENDPOINTS.md` no está presente. Se consultó el OpenAPI local en `http://localhost:8000/openapi.json`: expone cinco rutas, parámetros y estados, pero declara respuestas genéricas. Swagger marca `Authorization` como opcional y no lista `401`; la implementación actual sí exige una identidad válida y responde `401` ante un token inválido. Antes de implementar, debe acordarse cómo documentar esa diferencia sin cambiar el contrato que usan los clientes.

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

## Orden y verificación posterior

1. Confirmar con el emisor los parámetros JWT y resolver la discrepancia documental del header/respuesta `401` sin alterar rutas ni formatos de éxito.
2. Añadir primero las pruebas de caracterización indicadas para ambos hallazgos y registrar qué fallan por los defectos actuales.
3. Implementar H-01 y H-02 en sus módulos respectivos, sin incorporar valores de producción; mantener la meta de cobertura de al menos 85% para el código modificado.
4. Ejecutar las pruebas específicas y la suite completa; comparar rutas, solicitudes y respuestas con el OpenAPI disponible. No considerar verificados los campos que Swagger publica como esquemas genéricos hasta recuperar un contrato detallado.

Este plan no afirma que las pruebas se hayan ejecutado. La verificación de `iss`, `aud`, algoritmo, claims y rotación depende de la coordinación externa indicada arriba.