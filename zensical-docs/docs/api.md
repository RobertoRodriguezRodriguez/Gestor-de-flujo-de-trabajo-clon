---
icon: lucide/code-2
---

# API REST

El gestor expone una API REST bajo `/api/v1/` con autenticación JWT. Está construida con Django REST Framework.

## Autenticación

La API usa tokens JWT (JSON Web Tokens). Necesitas obtener un par de tokens e incluir el `access` token en la cabecera de cada petición.

### Obtener tokens

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "email": "usuario@ejemplo.com",
  "password": "tu-contraseña"
}
```

**Respuesta:**

```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

!!! warning "Rate limiting"
    El endpoint de obtención de token tiene límite de peticiones (`django-ratelimit`) para proteger contra ataques de fuerza bruta.

### Usar el token

Incluye el `access` token en la cabecera `Authorization`:

```http
GET /api/v1/me/
Authorization: Bearer eyJ...
```

### Renovar el token

```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ..."
}
```

### Verificar el token

```http
POST /api/v1/auth/token/verify/
Content-Type: application/json

{
  "token": "eyJ..."
}
```

### Revocar el token

```http
POST /api/v1/auth/token/revoke/
Authorization: Bearer eyJ...
```

---

## Endpoints

### Usuario actual

```http
GET /api/v1/me/
```

Devuelve el perfil del usuario autenticado.

---

### Proyectos

#### Listar proyectos

```http
GET /api/v1/projects/
```

#### Crear proyecto

```http
POST /api/v1/projects/
Content-Type: application/json

{
  "name": "Mi proyecto",
  "key": "MP",
  "organization": "<uuid-org>",
  "status": "active",
  "priority": "medium"
}
```

#### Obtener proyecto

```http
GET /api/v1/projects/<uuid>/
```

#### Actualizar proyecto

```http
PUT /api/v1/projects/<uuid>/
```

---

### Tareas

#### Listar tareas de un proyecto

```http
GET /api/v1/projects/<project_uuid>/tasks/
```

#### Crear tarea

```http
POST /api/v1/projects/<project_uuid>/tasks/
Content-Type: application/json

{
  "title": "Implementar login",
  "type": "task",
  "status": "backlog",
  "priority": "high",
  "estimated_hours": 4
}
```

#### Obtener tarea

```http
GET /api/v1/projects/<project_uuid>/tasks/<task_uuid>/
```

#### Actualizar tarea

```http
PUT /api/v1/projects/<project_uuid>/tasks/<task_uuid>/
```

#### Eliminar tarea

```http
DELETE /api/v1/projects/<project_uuid>/tasks/<task_uuid>/
```

---

### Comentarios

#### Listar comentarios de una tarea

```http
GET /api/v1/projects/<project_uuid>/tasks/<task_uuid>/comments/
```

#### Crear comentario

```http
POST /api/v1/projects/<project_uuid>/tasks/<task_uuid>/comments/
Content-Type: application/json

{
  "content": "Esto está listo para revisión."
}
```

#### Eliminar comentario

```http
DELETE /api/v1/projects/<project_uuid>/tasks/<task_uuid>/comments/<comment_uuid>/
```

---

## Valores de referencia

### Estados de tarea (`status`)

| Valor | Descripción |
|-------|-------------|
| `backlog` | Backlog |
| `todo` | Por hacer |
| `in_progress` | En progreso |
| `in_review` | En revisión |
| `done` | Hecho |

### Tipos de tarea (`type`)

| Valor | Descripción |
|-------|-------------|
| `task` | Tarea |
| `bug` | Bug |
| `story` | Historia |
| `epic` | Épica |
| `subtask` | Subtarea |

### Prioridades (`priority`)

| Valor | Descripción |
|-------|-------------|
| `low` | Baja |
| `medium` | Media |
| `high` | Alta |
| `critical` | Crítica |

### Roles de proyecto (`role`)

| Valor | Descripción |
|-------|-------------|
| `owner` | Propietario |
| `manager` | Manager |
| `developer` | Desarrollador |
| `viewer` | Observador |
