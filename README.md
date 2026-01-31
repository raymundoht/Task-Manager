# Task Manager

Aplicación de gestión de tareas con diseño tipo React, backend en Python (Flask) y base de datos MongoDB. Sin login.

## Requisitos

- Python 3.8+
- MongoDB (Atlas o local)

## Instalación

```bash
cd project
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Configuración

Copia `.env.example` a `.env` y ajusta si es necesario:

- `PORT=3000` — Puerto del servidor
- `MONGODB_URI` — URI de conexión a MongoDB

Por defecto ya está configurado con tu URI de MongoDB Atlas.

## Ejecutar

```bash
python app.py
```

Abre en el navegador: **http://localhost:3000**

## Secciones

- **Tareas** — Crear, editar, eliminar tareas. Estadísticas y tabla.
- **Proyectos** — CRUD de proyectos (Nombre, Descripción).
- **Comentarios** — Agregar comentarios por ID de tarea y cargar comentarios (acepta ID completo o últimos 6 caracteres).
- **Historial** — Ver historial de cambios por tarea o todo.
- **Notificaciones** — Cargar y ver notificaciones.
- **Búsqueda** — Búsqueda avanzada por texto, estado, prioridad y proyecto.
- **Reportes** — Reportes de tareas, proyectos y usuarios; exportar a CSV.

## Base de datos (MongoDB)

Colecciones usadas:

- `tasks` — Tareas (titulo, descripción, estado, prioridad, proyecto, asignado, fecha vencimiento, horas estimadas)
- `projects` — Proyectos (nombre, descripción)
- `comments` — Comentarios por tarea (task_id, comentario)
- `history` — Historial de cambios en tareas
- `notifications` — Notificaciones
- `users` — Usuarios (para "Asignado a"; se crea "admin" automáticamente si no hay ninguno)
