from app import db
from app.models.task import Task
from app.models.goal import Goal
from flask import Blueprint, jsonify, abort, make_response, request
from sqlalchemy import desc
import datetime
import requests
import os
from dotenv import load_dotenv

load_dotenv()

task_bp = Blueprint("task", __name__, url_prefix="/tasks")
goal_bp = Blueprint("goal", __name__, url_prefix="/goals")

def validate_id(id):
    try:
        id = int(id)
    except ValueError:
        abort(make_response({"error": f"{id} is an invalid ID. ID must be an integer."}, 400))
    
    return id

def retrieve_object(id, Model):
    if Model == Task:
        model_type = "task"
    elif Model == Goal:
        model_type = "goal"
    
    model = Model.query.get(id)

    if not model:
        abort(make_response({"error": f"{model_type} {id} not found"}, 404))
    
    return model

def create_task_response_body(task):
    response_body = {
            "task": {
                "id": task.task_id,
                "title": task.title,
                "description": task.description,
                "is_complete": bool(task.completed_at)
            }
    }

    if task.goal_id:
        response_body["task"]["goal_id"] = task.goal_id

    return response_body

def create_goal_response_body(goal):
    response_body = {
        "goal": {
            "id": goal.goal_id,
            "title": goal.title
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
    
    return jsonify(response), 200

@task_bp.route("/<task_id>", methods=["GET"])
def read_task(task_id):
    task_id = validate_id(task_id)
    task = retrieve_object(task_id, Task)
    
    response_body = create_task_response_body(task)

    return jsonify(response_body), 200

@task_bp.route("", methods=["POST"])
def create_task():
    request_body = request.get_json()

    # create task with required attributes
    try:
        task = Task(
            title=request_body["title"],
            description=request_body["description"]
            )
    except KeyError:
        return jsonify({"details": f"Invalid data"}), 400

    # add optional attributes to task if data is provided
    try:
        task.completed_at = request_body["completed_at"]
    except KeyError:
        pass
    
    db.session.add(task)
    db.session.commit()

    response_body = create_task_response_body(task)

    return jsonify(response_body), 201


@task_bp.route("/<task_id>", methods=["PUT"])
def replace_task(task_id):
    task_id = validate_id(task_id)
    task = retrieve_object(task_id, Task)
    
    request_body = request.get_json()

    # replace task with required attributes
    try:
        task.title = request_body["title"]
        task.description = request_body["description"]
    except KeyError:
        return jsonify({"details": f"Invalid data"}), 400

    # replace optional attributes if data is provided
    try:
        task.completed_at = request_body["completed_at"]
    except KeyError:
        pass

    db.session.commit()

    response_body = create_task_response_body(task)

    return jsonify(response_body), 200

@task_bp.route("/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    task_id = validate_id(task_id)
    task = retrieve_object(task_id, Task)
    
    title = task.title

    db.session.delete(task)
    db.session.commit()

    response_body = {'details': f'Task {task_id} "{title}" successfully deleted'}

    return jsonify(response_body), 200

@task_bp.route("/<task_id>/mark_complete", methods=["PATCH"])
def mark_complete(task_id):
    task_id = validate_id(task_id)
    task = retrieve_object(task_id, Task)
    
    # change completed at time and commit to database
    task.completed_at = datetime.datetime.now()
    db.session.commit()

    # send automatic slack message
    try:
        message = "Someone just completed the task " + task.title
        message_info = {"channel": "task-notifications", "text": message}
        api_key = "Bearer " + os.environ.get("SLACK_BOT_USER_OAUTH_TOKEN", "")
        headers = {"Authorization": api_key}

        r = requests.post("https://slack.com/api/chat.postMessage", params=message_info, headers=headers)
    except:
        return jsonify({"error": "slack message could not be sent"}), 500

    # HTTP response body
    response_body = create_task_response_body(task)
    
    return jsonify(response_body), 200

@task_bp.route("/<task_id>/mark_incomplete", methods=["PATCH"])
def mark_incomplete(task_id):
    task_id = validate_id(task_id)
    task = retrieve_object(task_id, Task)
    
    # change completed at time to None and commit to database
    task.completed_at = None
    db.session.commit()

    response_body = create_task_response_body(task)
    
    return jsonify(response_body), 200

@goal_bp.route("", methods=["POST"])
def create_goal():
    request_body = request.get_json()
    
    try:
        goal = Goal(title=request_body["title"])
    except KeyError:
        return jsonify({"details": "Invalid data"}), 400

    db.session.add(goal)
    db.session.commit()

    response_body = create_goal_response_body(goal)

    return jsonify(response_body), 201

@goal_bp.route("", methods=["GET"])
def read_all_goals():

    goals = Goal.query.all()
    response_body = []

    for goal in goals:
        response_body.append({
            "id": goal.goal_id,
            "title": goal.title
        })

    return jsonify(response_body), 200

@goal_bp.route("/<goal_id>", methods=["GET"])
def read_specific_goal(goal_id):
    goal_id = validate_id(goal_id)
    goal = retrieve_object(goal_id, Goal)
    
    response_body = create_goal_response_body(goal)

    return jsonify(response_body), 200

@goal_bp.route("/<goal_id>", methods=["PUT"])
def replace_goal(goal_id):
    goal_id = validate_id(goal_id)
    goal = retrieve_object(goal_id, Goal)

    request_body = request.get_json()

    try:
        goal.title = request_body["title"]
    except KeyError:
        return jsonify({"details": f"Invalid data"}), 400

    db.session.commit()

    response_body = create_goal_response_body(goal)

    return jsonify(response_body), 200

@goal_bp.route("/<goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    goal_id = validate_id(goal_id)
    goal = retrieve_object(goal_id, Goal)

    title = goal.title
    
    db.session.delete(goal)
    db.session.commit()
    
    response_body = {"details": f'Goal {goal_id} "{title}" successfully deleted'}

    return jsonify(response_body), 200

@goal_bp.route("/<goal_id>/tasks", methods=["POST"])
def send_list_of_tasks_to_goal(goal_id):
    goal_id = validate_id(goal_id)
    goal = retrieve_object(goal_id, Goal)

    request_body = request.get_json()

    # verify task_ids list in request body
    try:
        task_ids = request_body["task_ids"]
    except KeyError:
        return jsonify({"details": f"Invalid data"}), 400

    if not isinstance(task_ids, list):
        return jsonify({"details": "Expected list of task ids"}), 400

    # validate task_ids and append tasks to list of tasks
    tasks = []

    for task_id in task_ids:
        task_id = validate_id(task_id)
        task = retrieve_object(task_id, Task)
        tasks.append(task)

    # update goal_id for each task
    for task in tasks:
        task.goal_id = goal_id
    
    db.session.commit()

    # create task_ids list using updated data
    task_ids = []
    for task in goal.tasks:
        task_ids.append(task.task_id)
    
    response_body = {
        "id": goal.goal_id,
        "task_ids": task_ids
    }

    return jsonify(response_body), 200

@goal_bp.route("/<goal_id>/tasks", methods=["GET"])
def read_tasks_of_one_goal(goal_id):
    goal_id = validate_id(goal_id)
    goal = retrieve_object(goal_id, Goal)
    
    task_response = []

    for task in goal.tasks:
        task_response.append({
            "id": task.task_id,
            "goal_id": task.goal_id,
            "title": task.title,
            "description": task.description,
            "is_complete": bool(task.completed_at)
        })

    response_body = {
        "id": goal_id,
        "title": goal.title,
        "tasks": task_response
    }

    return jsonify(response_body), 200