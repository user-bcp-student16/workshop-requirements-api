# Workshop Requirements API

Contrato verificado contra `app/main.py`, `app/schemas.py`, `app/security.py`, los servicios/repositorios y `tests/test_api.py`. La API se ejecuta localmente en `http://localhost:8000`; Swagger publica OpenAPI 3.1.0, versión `0.1.0`, con modelos Pydantic para las respuestas.

## Autenticación común

Las cinco operaciones requieren en la práctica un token aceptado por la dependencia actual, enviado exactamente como `Authorization: Bearer <token>`. Aunque Swagger marca el parámetro como opcional, el código responde `401` si falta o no es válido, con cuerpo genérico `{"detail":"Invalid token"}`.

El verificador actual decodifica Base64 y espera cuatro partes separadas por `|`: username, role, expiración Unix y una clave legacy. No es JWT, no verifica firma, issuer ni audience. La API no ofrece un endpoint público para emitir tokens. Por eso, `<TOKEN_BEARER_VALIDO>` en los ejemplos es un marcador, no una credencial utilizable. **Pregunta abierta:** ¿qué mecanismo aprobado debe usar un cliente para obtener tokens en el entorno local? No copiar una credencial de desarrollo a otros entornos.

Los ejemplos de respuestas muestran valores posibles según los datos iniciales. El ID, la fecha de creación, el directorio configurado y la respuesta del backend pueden variar.

## `GET /api/tasks`

### 1. Qué hace

Lista las tareas cuyo propietario es el usuario identificado por el token.

### 2. Autenticación

Requerida. Header exacto: `Authorization: Bearer <TOKEN_BEARER_VALIDO>`.

### 3. Request

No tiene cuerpo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `owner` (query) | string | No | Se conserva por compatibilidad, pero no selecciona el propietario; la consulta usa el username de la identidad. |
| `Authorization` (header) | string | Sí en ejecución | Bearer token aceptado por el verificador legacy. |

Ejemplo:

```http
GET /api/tasks?owner=trainer HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN_BEARER_VALIDO>
```

### 4. Response exitosa

Estado `200 OK`.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Identificador de la tarea. |
| `title` | string | Título. |
| `description` | string | Descripción. |
| `status` | string | Estado almacenado. |
| `owner` | string | Username autenticado. |
| `priority` | string | Prioridad almacenada. |
| `createdAt` | string | Fecha/hora de SQLite (`datetime('now')`). |

Ejemplo:

```json
[
	{
		"id": 1,
		"title": "Refactor login",
		"description": "Separar responsabilidades en frontend",
		"status": "TODO",
		"owner": "student",
		"priority": "HIGH",
		"createdAt": "2026-10-19 10:30:00"
	}
]
```

### 5. Respuestas de error

- `401 Unauthorized`: falta el header o el token no pasa la validación. Ejemplo comprobado al omitir el header:

```json
{"detail":"Invalid token"}
```

- `422 Unprocessable Content`: Swagger anuncia el error genérico de validación, pero `owner` es `string | null` y no se identificó en el código una entrada concreta que lo dispare. **Pregunta abierta:** confirmar si se desea sostener este estado como parte del contrato. No se inventa un cuerpo específico.
- `500 Internal Server Error`: una excepción no capturada de SQLite puede llegar al servidor ASGI. La ruta no define un cuerpo estable. **Pregunta abierta:** definir el contrato de errores internos si los clientes deben manejarlo.

### 6. Notas de seguridad

El parámetro `owner` no concede acceso a otro usuario; se ignora para autorización. La identidad usada por la consulta sigue dependiendo del token legacy no firmado, por lo que no debe considerarse una autenticación segura.

## `POST /api/tasks`

### 1. Qué hace

Crea una tarea asignada al usuario identificado por el token.

### 2. Autenticación

Requerida. Header exacto: `Authorization: Bearer <TOKEN_BEARER_VALIDO>`.

### 3. Request

Cuerpo requerido `application/json`, recibido como un `RootModel` Pydantic cuyo valor raíz es un objeto JSON con propiedades arbitrarias. Los campos conocidos se convierten a string al accederlos; no se aplican enums ni restricciones por campo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `title` (body) | valor JSON; se convierte a string | No | Título. Si se omite, se almacena `""`. |
| `description` (body) | valor JSON; se convierte a string | No | Descripción. Si se omite, se almacena `""`. |
| `status` (body) | valor JSON; se convierte a string | No | Estado. Default `"TODO"`; no hay validación de enum. |
| `priority` (body) | valor JSON; se convierte a string | No | Prioridad. Default `"MEDIUM"`; no hay validación de enum. |
| `owner` (body) | valor JSON | No | No se usa; el owner siempre se toma del username autenticado. |
| `Authorization` (header) | string | Sí en ejecución | Bearer token aceptado por el verificador legacy. |

Ejemplo:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN_BEARER_VALIDO>
Content-Type: application/json

{
	"title": "Add tests",
	"description": "Improve coverage",
	"status": "TODO",
	"priority": "HIGH",
	"owner": "trainer"
}
```

### 4. Response exitosa

Estado `201 Created`. El objeto contiene los mismos campos de tarea descritos en `GET /api/tasks`.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Identificador asignado por SQLite. |
| `title` | string | Título convertido a string. |
| `description` | string | Descripción convertida a string. |
| `status` | string | Estado convertido a string. |
| `owner` | string | Username autenticado; ignora `owner` enviado en el cuerpo. |
| `priority` | string | Prioridad convertida a string. |
| `createdAt` | string | Fecha/hora de SQLite (`datetime('now')`). |

Ejemplo:

```json
{
	"id": 4,
	"title": "Add tests",
	"description": "Improve coverage",
	"status": "TODO",
	"owner": "student",
	"priority": "HIGH",
	"createdAt": "2026-10-19 10:30:00"
}
```

### 5. Respuestas de error

- `401 Unauthorized`: falta el header o el token no pasa la validación. Ejemplo:

```json
{"detail":"Invalid token"}
```

- `422 Unprocessable Content`: el cuerpo falta o no es un objeto JSON. Ejemplo real consultado con un array JSON:

```json
{"detail":[{"type":"dict_type","loc":["body"],"msg":"Input should be a valid dictionary","input":[]}]}
```

- `500 Internal Server Error`: puede ocurrir si falla la inserción, commit o lectura SQLite. La ruta no define un cuerpo estable. **Pregunta abierta:** definir el formato de fallos internos.

### 6. Notas de seguridad

El cuerpo acepta propiedades adicionales, pero `owner` no se usa para autorizar ni asignar la tarea. Los valores recibidos se convierten con `str()` y no se validan contra enums. La identidad depende del token legacy no firmado.

## `GET /api/summary`

### 1. Qué hace

Resume el total, los estados y las tareas abiertas de prioridad alta del usuario autenticado.

### 2. Autenticación

Requerida. Header exacto: `Authorization: Bearer <TOKEN_BEARER_VALIDO>`.

### 3. Request

No tiene cuerpo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `owner` (query) | string | No | Se conserva por compatibilidad, pero se ignora; se resume el username autenticado. |
| `Authorization` (header) | string | Sí en ejecución | Bearer token aceptado por el verificador legacy. |

Ejemplo:

```http
GET /api/summary?owner=trainer HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN_BEARER_VALIDO>
```

### 4. Response exitosa

Estado `200 OK`.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | string | Username autenticado. |
| `total` | integer | Cantidad de tareas del usuario. |
| `byStatus` | object<string, integer> | Cantidad de tareas agrupadas por el valor almacenado de `status`. |
| `highPriorityOpen` | integer | Tareas `HIGH` cuyo estado no es `DONE` ni `ARCHIVED`. |

Ejemplo para los datos iniciales del usuario `student`:

```json
{
	"owner": "student",
	"total": 2,
	"byStatus": {
		"TODO": 1,
		"IN_PROGRESS": 1
	},
	"highPriorityOpen": 1
}
```

### 5. Respuestas de error

- `401 Unauthorized`: falta el header o el token no pasa la validación. Ejemplo:

```json
{"detail":"Invalid token"}
```

- `422 Unprocessable Content`: Swagger anuncia validación genérica, pero `owner` es `string | null` y no se identificó una entrada concreta que la dispare. **Pregunta abierta:** confirmar si se sostiene este estado en el contrato.
- `500 Internal Server Error`: puede ocurrir si falla una consulta SQLite; la ruta no define un cuerpo estable. **Pregunta abierta:** definir el formato de fallos internos.

### 6. Notas de seguridad

La autorización ignora el `owner` de query y consulta exclusivamente el username autenticado. La autenticidad de ese username depende del verificador Base64 legacy, que no valida firma.

## `POST /api/requirements`

### 1. Qué hace

Guarda el archivo de requerimientos recibido y devuelve sus datos de almacenamiento.

### 2. Autenticación

Requerida. Header exacto: `Authorization: Bearer <TOKEN_BEARER_VALIDO>`.

### 3. Request

Cuerpo `multipart/form-data`.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `file` (form) | archivo binario | Sí | Archivo que se leerá y guardará. |
| `Authorization` (header) | string | Sí en ejecución | Bearer token aceptado por el verificador legacy. |

Ejemplo:

```http
POST /api/requirements HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN_BEARER_VALIDO>
Content-Type: multipart/form-data; boundary=Boundary

--Boundary
Content-Disposition: form-data; name="file"; filename="requirements.txt"
Content-Type: text/plain

Login must be accessible
--Boundary--
```

### 4. Response exitosa

Estado `201 Created`.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | string | Username autenticado. |
| `fileName` | string o null | Nombre recibido en la parte multipart. |
| `storedAt` | string | Ruta construida con `pathlib` bajo `WORKSHOP_UPLOAD_DIR`; default `uploads`, con separadores propios del sistema operativo. |
| `size` | integer | Cantidad de bytes leídos. |

Ejemplo con el directorio default y el contenido mostrado en la solicitud (24 bytes):

```json
{
	"owner": "student",
	"fileName": "requirements.txt",
	"storedAt": "uploads\\requirements.txt",
	"size": 24
}
```

### 5. Respuestas de error

- `401 Unauthorized`: falta el header o el token no pasa la validación. Ejemplo:

```json
{"detail":"Invalid token"}
```

- `422 Unprocessable Content`: falta el campo `file` o FastAPI no puede validarlo como archivo. Ejemplo real consultado sin enviar archivo:

```json
{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}
```

- `500 Internal Server Error`: un fallo no capturado al leer o escribir el archivo puede llegar al servidor ASGI. No hay cuerpo estable definido por la ruta. **Pregunta abierta:** definir formato para errores de almacenamiento.

### 6. Notas de seguridad

El código usa `file.filename` directamente para construir la ruta y lee el archivo completo en memoria. No hay validación de extensión, normalización ni límite de tamaño. No subas archivos no confiables ni expongas este servicio.

## `GET /api/backend-health`

### 1. Qué hace

Consulta el endpoint de salud del backend de autenticación y devuelve el resultado de esa llamada.

### 2. Autenticación

Requerida. Header exacto: `Authorization: Bearer <TOKEN_BEARER_VALIDO>`.

### 3. Request

No tiene query ni cuerpo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `Authorization` (header) | string | Sí en ejecución | Bearer token aceptado por el verificador legacy. |

Ejemplo:

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN_BEARER_VALIDO>
```

La URL consultada no es un parámetro request: se toma de `AUTH_HEALTH_URL`; default `http://localhost:8080/q/health`.

### 4. Response exitosa

Estado HTTP `200 OK`.

| Campo | Tipo | Descripción |
|---|---|---|
| `requestedBy` | string | Username autenticado. |
| `status` | integer | Status HTTP devuelto por el backend consultado; `0` si la llamada falla. |
| `body` | string | Cuerpo del backend decodificado como UTF-8; mensaje genérico si falla una llamada de red prevista. |

Ejemplo posible cuando el backend responde con HTTP 200 y cuerpo `OK`:

```json
{
	"requestedBy": "student",
	"status": 200,
	"body": "OK"
}
```

### 5. Respuestas de error

- `401 Unauthorized`: falta el header o el token no pasa la validación. Ejemplo:

```json
{"detail":"Invalid token"}
```

- Fallo de red previsto al consultar el backend: no es un error HTTP de esta API; responde `200 OK` con `status: 0` y mensaje genérico:

```json
{
	"requestedBy": "student",
	"status": 0,
	"body": "Backend health request failed"
}
```

- `422 Unprocessable Content`: Swagger anuncia validación genérica, pero esta ruta no declara parámetros ni cuerpo que la disparen. **Pregunta abierta:** confirmar si se mantiene esta respuesta genérica.

### 6. Notas de seguridad

La URL destino se controla mediante `AUTH_HEALTH_URL`, no por el request. Los fallos de red previstos se convierten a un mensaje genérico y no exponen el texto de excepción. La identidad depende del token legacy no firmado.

## Preguntas abiertas del contrato

1. ¿Cómo obtiene un cliente autorizado un token legacy sin divulgar la clave embebida ni depender de leer el código?
2. ¿Debe documentarse `422` para los GET y para `GET /api/backend-health`? Swagger lo genera, pero sus parámetros actuales no tienen una restricción inválida identificable.
3. ¿Qué formato de cuerpo deben tener los errores `500` no capturados? Las rutas no lo definen.
4. ¿Qué esquema de respuesta quiere el backend de salud y qué valores reales puede devolver en `body`? El contenido depende del servicio configurado.
