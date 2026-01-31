import os
import csv
import io
from datetime import datetime, UTC
from flask import Flask, render_template, request, jsonify, redirect, url_for
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

client = MongoClient(MONGODB_URI)
db = client["proyectoclas"]

print("✅ Conectado a MongoDB")
print(db.list_collection_names())

# Colecciones
tasks_coll = db.tasks
projects_coll = db.projects
comments_coll = db.comments
history_coll = db.history
notifications_coll = db.notifications
users_coll = db.users


# Opciones por defecto
ESTADOS = ["Pendiente", "En progreso", "Completada", "Cancelada"]
PRIORIDADES = ["Baja", "Media", "Alta"]


def get_projects_list():
    return [{"_id": str(p["_id"]), "nombre": p.get("nombre", "")} for p in projects_coll.find()]


def get_users_list():
    users = list(users_coll.find())
    if not users:
        users_coll.insert_one({"nombre": "admin"})
        users = list(users_coll.find())
    return [{"_id": str(u["_id"]), "nombre": u.get("nombre", "Sin nombre")} for u in users]


def log_history(task_id, action, details):
    history_coll.insert_one({
        "task_id": task_id,
        "action": action,
        "details": details,
        "created_at": datetime.utcnow()
    })


# ---------- Vistas (páginas) ----------

@app.route("/")
def index():
    return redirect(url_for("tasks"))


@app.route("/tareas")
def tasks():
    return render_template("tasks.html", activo="tareas")


@app.route("/proyectos")
def projects():
    return render_template("projects.html", activo="proyectos")


@app.route("/comentarios")
def comments():
    return render_template("comments.html", activo="comentarios")


@app.route("/historial")
def history():
    return render_template("history.html", activo="historial")


@app.route("/notificaciones")
def notifications():
    return render_template("notifications.html", activo="notificaciones")


@app.route("/busqueda")
def search():
    return render_template("search.html", activo="busqueda")


@app.route("/reportes")
def reports():
    return render_template("reports.html", activo="reportes")


# ---------- API Tareas ----------

@app.route("/api/tareas", methods=["GET"])
def api_tareas_list():
    tareas = list(tasks_coll.find().sort("_id", DESCENDING))
    for t in tareas:
        t["_id"] = str(t["_id"])
        if "fecha_vencimiento" in t and t["fecha_vencimiento"]:
            if hasattr(t["fecha_vencimiento"], "strftime"):
                t["fecha_vencimiento"] = t["fecha_vencimiento"].strftime("%d/%m/%Y")
    return jsonify(tareas)


@app.route("/api/tareas/estadisticas", methods=["GET"])
def api_tareas_stats():
    total = tasks_coll.count_documents({})
    completadas = tasks_coll.count_documents({"estado": "Completada"})
    pendientes = tasks_coll.count_documents({"estado": "Pendiente"})
    alta_prioridad = tasks_coll.count_documents({"prioridad": "Alta"})
    hoy = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    vencidas = tasks_coll.count_documents({
        "fecha_vencimiento": {"$lt": hoy},
        "estado": {"$ne": "Completada"}
    })
    return jsonify({
        "total": total,
        "completadas": completadas,
        "pendientes": pendientes,
        "alta_prioridad": alta_prioridad,
        "vencidas": vencidas
    })


@app.route("/api/tareas", methods=["POST"])
def api_tarea_create():
    data = request.get_json()
    doc = {
        "titulo": data.get("titulo", ""),
        "descripcion": data.get("descripcion", ""),
        "estado": data.get("estado", "Pendiente"),
        "prioridad": data.get("prioridad", "Baja"),
        "proyecto_id": data.get("proyecto_id") or None,
        "asignado_id": data.get("asignado_id") or None,
        "horas_estimadas": data.get("horas_estimadas", ""),
        "created_at": datetime.utcnow()
    }
    fecha = data.get("fecha_vencimiento")
    if fecha:
        try:
            doc["fecha_vencimiento"] = datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            doc["fecha_vencimiento"] = None
    else:
        doc["fecha_vencimiento"] = None

    result = tasks_coll.insert_one(doc)
    log_history(str(result.inserted_id), "creación", {"titulo": doc["titulo"]})
    doc["_id"] = str(result.inserted_id)
    if doc.get("fecha_vencimiento") and hasattr(doc["fecha_vencimiento"], "strftime"):
        doc["fecha_vencimiento"] = doc["fecha_vencimiento"].strftime("%d/%m/%Y")
    return jsonify(doc), 201


@app.route("/api/tareas/<id>", methods=["PUT"])
def api_tarea_update(id):
    data = request.get_json()
    update = {
        "titulo": data.get("titulo"),
        "descripcion": data.get("descripcion"),
        "estado": data.get("estado"),
        "prioridad": data.get("prioridad"),
        "proyecto_id": data.get("proyecto_id"),
        "asignado_id": data.get("asignado_id"),
        "horas_estimadas": data.get("horas_estimadas"),
    }
    fecha = data.get("fecha_vencimiento")
    if fecha is not None:
        if fecha:
            try:
                update["fecha_vencimiento"] = datetime.strptime(fecha, "%Y-%m-%d")
            except ValueError:
                update["fecha_vencimiento"] = None
        else:
            update["fecha_vencimiento"] = None

    update = {k: v for k, v in update.items() if v is not None}
    if update:
        tasks_coll.update_one({"_id": ObjectId(id)}, {"$set": update})
        log_history(id, "actualización", update)
    t = tasks_coll.find_one({"_id": ObjectId(id)})
    if not t:
        return jsonify({"error": "No encontrada"}), 404
    t["_id"] = str(t["_id"])
    if t.get("fecha_vencimiento") and hasattr(t["fecha_vencimiento"], "strftime"):
        t["fecha_vencimiento"] = t["fecha_vencimiento"].strftime("%d/%m/%Y")
    return jsonify(t)


@app.route("/api/tareas/<id>", methods=["DELETE"])
def api_tarea_delete(id):
    result = tasks_coll.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        log_history(id, "eliminación", {})
        return jsonify({"ok": True}), 200
    return jsonify({"error": "No encontrada"}), 404


# ---------- API Proyectos ----------

@app.route("/api/proyectos", methods=["GET"])
def api_proyectos_list():
    proyectos = list(projects_coll.find())
    for p in proyectos:
        p["_id"] = str(p["_id"])
    return jsonify(proyectos)


@app.route("/api/proyectos", methods=["POST"])
def api_proyecto_create():
    data = request.get_json()
    doc = {
        "nombre": data.get("nombre", ""),
        "descripcion": data.get("descripcion", "")
    }
    result = projects_coll.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return jsonify(doc), 201


@app.route("/api/proyectos/<id>", methods=["PUT"])
def api_proyecto_update(id):
    data = request.get_json()
    update = {k: v for k, v in {
        "nombre": data.get("nombre"),
        "descripcion": data.get("descripcion")
    }.items() if v is not None}
    if update:
        projects_coll.update_one({"_id": ObjectId(id)}, {"$set": update})
    p = projects_coll.find_one({"_id": ObjectId(id)})
    if not p:
        return jsonify({"error": "No encontrado"}), 404
    p["_id"] = str(p["_id"])
    return jsonify(p)


@app.route("/api/proyectos/<id>", methods=["DELETE"])
def api_proyecto_delete(id):
    result = projects_coll.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        return jsonify({"ok": True}), 200
    return jsonify({"error": "No encontrado"}), 404


# ---------- API Comentarios ----------

@app.route("/api/comentarios", methods=["POST"])
def api_comment_create():
    data = request.get_json()
    task_id = (data.get("task_id") or "").strip()
    texto = data.get("comentario", "")
    if not task_id:
        return jsonify({"error": "task_id requerido"}), 400
    task_id = _resolve_task_id(task_id)
    doc = {
        "task_id": task_id,
        "comentario": texto,
        "created_at": datetime.utcnow()
    }
    result = comments_coll.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return jsonify(doc), 201


def _resolve_task_id(task_id):
    """Acepta ID completo (24 chars) o corto (últimos 6 chars)."""
    if len(task_id) == 24:
        try:
            if tasks_coll.find_one({"_id": ObjectId(task_id)}):
                return task_id
        except Exception:
            pass
    for t in tasks_coll.find({}):
        sid = str(t["_id"])
        if sid.endswith(task_id) or sid == task_id:
            return sid
    return task_id


@app.route("/api/comentarios/tarea/<task_id>", methods=["GET"])
def api_comments_by_task(task_id):
    task_id = _resolve_task_id(task_id)
    comentarios = list(comments_coll.find({"task_id": task_id}).sort("created_at", DESCENDING))
    for c in comentarios:
        c["_id"] = str(c["_id"])
        if c.get("created_at") and hasattr(c["created_at"], "strftime"):
            c["created_at"] = c["created_at"].strftime("%d/%m/%Y %H:%M")
    return jsonify(comentarios)


# ---------- API Historial ----------

@app.route("/api/historial", methods=["GET"])
def api_historial_all():
    task_id = request.args.get("task_id")
    if task_id:
        items = list(history_coll.find({"task_id": task_id}).sort("created_at", DESCENDING))
    else:
        items = list(history_coll.find().sort("created_at", DESCENDING))
    for h in items:
        h["_id"] = str(h["_id"])
        if h.get("created_at") and hasattr(h["created_at"], "strftime"):
            h["created_at"] = h["created_at"].strftime("%d/%m/%Y %H:%M")
    return jsonify(items)


# ---------- API Notificaciones ----------

@app.route("/api/notificaciones", methods=["GET"])
def api_notificaciones_list():
    notifs = list(notifications_coll.find().sort("created_at", DESCENDING).limit(100))
    for n in notifs:
        n["_id"] = str(n["_id"])
        if n.get("created_at") and hasattr(n["created_at"], "strftime"):
            n["created_at"] = n["created_at"].strftime("%d/%m/%Y %H:%M")
    return jsonify(notifs)


# ---------- API Búsqueda ----------

@app.route("/api/busqueda", methods=["GET"])
def api_busqueda():
    texto = request.args.get("texto", "").strip()
    estado = request.args.get("estado", "")
    prioridad = request.args.get("prioridad", "")
    proyecto_id = request.args.get("proyecto_id", "")

    query = {}
    if texto:
        query["$or"] = [
            {"titulo": {"$regex": texto, "$options": "i"}},
            {"descripcion": {"$regex": texto, "$options": "i"}}
        ]
    if estado and estado != "Todos":
        query["estado"] = estado
    if prioridad and prioridad != "Todas":
        query["prioridad"] = prioridad
    if proyecto_id and proyecto_id != "Todos":
        query["proyecto_id"] = proyecto_id

    tareas = list(tasks_coll.find(query).sort("_id", DESCENDING))
    for t in tareas:
        t["_id"] = str(t["_id"])
        if t.get("fecha_vencimiento") and hasattr(t["fecha_vencimiento"], "strftime"):
            t["fecha_vencimiento"] = t["fecha_vencimiento"].strftime("%d/%m/%Y")
    return jsonify(tareas)


# ---------- API Reportes y CSV ----------

@app.route("/api/reportes/tareas", methods=["GET"])
def api_reportes_tareas():
    tareas = list(tasks_coll.find())
    return jsonify([{**t, "_id": str(t["_id"])} for t in tareas])


@app.route("/api/reportes/proyectos", methods=["GET"])
def api_reportes_proyectos():
    proyectos = list(projects_coll.find())
    return jsonify([{**p, "_id": str(p["_id"])} for p in proyectos])


@app.route("/api/reportes/usuarios", methods=["GET"])
def api_reportes_usuarios():
    usuarios = list(users_coll.find())
    return jsonify([{**u, "_id": str(u["_id"])} for u in usuarios])


@app.route("/api/export/tareas/csv")
def export_tareas_csv():
    tareas = list(tasks_coll.find())
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID", "Título", "Descripción", "Estado", "Prioridad", "Proyecto ID", "Asignado ID", "Fecha Vencimiento", "Horas Estimadas"])
    for t in tareas:
        fv = t.get("fecha_vencimiento")
        if fv and hasattr(fv, "strftime"):
            fv = fv.strftime("%d/%m/%Y")
        w.writerow([
            str(t["_id"]),
            t.get("titulo", ""),
            t.get("descripcion", ""),
            t.get("estado", ""),
            t.get("prioridad", ""),
            str(t.get("proyecto_id") or ""),
            str(t.get("asignado_id") or ""),
            fv or "",
            t.get("horas_estimadas", "")
        ])
    response = app.response_class(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=tareas.csv"
    return response


@app.route("/api/export/proyectos/csv")
def export_proyectos_csv():
    proyectos = list(projects_coll.find())
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID", "Nombre", "Descripción"])
    for p in proyectos:
        w.writerow([str(p["_id"]), p.get("nombre", ""), p.get("descripcion", "")])
    response = app.response_class(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=proyectos.csv"
    return response


@app.route("/api/export/usuarios/csv")
def export_usuarios_csv():
    usuarios = list(users_coll.find())
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID", "Nombre"])
    for u in usuarios:
        w.writerow([str(u["_id"]), u.get("nombre", "")])
    response = app.response_class(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=usuarios.csv"
    return response


# ---------- Datos para formularios (proyectos, usuarios) ----------

@app.route("/api/opciones/proyectos", methods=["GET"])
def api_opciones_proyectos():
    return jsonify(get_projects_list())


@app.route("/api/opciones/usuarios", methods=["GET"])
def api_opciones_usuarios():
    return jsonify(get_users_list())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
