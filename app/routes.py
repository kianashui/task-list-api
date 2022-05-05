from app import db
from app.models.task import Task
from flask import Blueprint, jsonify, abort, make_response, request
from sqlalchemy import desc
import datetime

task_bp = Blueprint("task", __name__, url_prefix="/tasks")

def validate_task_id(task_id):
    try:
        task_id = int(task_id)
    except ValueError:
        abort(make_response({"error": f"{task_id} is an invalid task ID. ID must be an integer."}, 400))

    task = Task.query.get(task_id)

    if not task:
        abort(make_response({"error": f"task {task_id} not found"}, 404))
    
    return task

def create_response_body(task):
    if task.completed_at:
        task_completed = True
    else:
        task_completed = False
    response_body = {
        "task": {
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "is_complete": task_completed
            }
    }
    return response_body

@task_bp.route("", methods=["GET"])
def read_all_tasks():
    sort_query = request.args.get("sort")

    if sort_query == "desc":
        tasks = Task.query.order_by(desc(Task.title))
    elif sort_query == "asc":
        tasks = Task.query.order_by(Task.title)
    else:
        tasks = Task.query.all()

    response = []

    for task in tasks:
        response.append({
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "is_complete": False
        })
    
    return jsonify(response)

@task_bp.route("/<task_id>", methods=["GET"])
def read_specific_task(task_id):
    task = validate_task_id(task_id)
    
    response_body = create_response_body(task)

    return jsonify(response_body)

@task_bp.route("", methods=["POST"])
def create_task():
    request_body = request.get_json()

    if "title" not in request_body or "description" not in request_body:
        return jsonify({"details": f"Invalid data"}), 400

    task = Task(title=request_body["title"],
        description=request_body["description"])
    
    if "completed_at" in request_body:
        task.completed_at = request_body["completed_at"]
    
    db.session.add(task)
    db.session.commit()

    response_body = create_response_body(task)

    return make_response(jsonify(response_body), 201)


@task_bp.route("/<task_id>", methods=["PUT"])
def replace_task(task_id):
    task = validate_task_id(task_id)

    request_body = request.get_json()

    if "title" not in request_body or "description" not in request_body:
        return jsonify({"details": f"Invalid data"}), 400

    task.title = request_body["title"]
    task.description = request_body["description"]

    if "completed_at" in request_body:
        task.completed_at = request_body["completed_at"]

    db.session.commit()

    response_body = create_response_body(task)

    return make_response(jsonify(response_body), 200)

@task_bp.route("/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = validate_task_id(task_id)
    title = task.title

    db.session.delete(task)
    db.session.commit()

    response_body = {'details': f'Task {task_id} "{title}" successfully deleted'}

    return make_response(jsonify(response_body), 200)

@task_bp.route("/<task_id>/mark_complete", methods=["PATCH"])
def mark_complete(task_id):
    task = validate_task_id(task_id)
    
    task.completed_at = datetime.datetime.now()
    db.session.commit()

    response_body = create_response_body(task)
    
    return make_response(jsonify(response_body), 200)

@task_bp.route("/<task_id>/mark_incomplete", methods=["PATCH"])
def mark_incomplete(task_id):
    task = validate_task_id(task_id)
    
    task.completed_at = None
    db.session.commit()

    response_body = create_response_body(task)
    
    return make_response(jsonify(response_body), 200)