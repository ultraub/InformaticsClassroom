from flask import render_template,request, jsonify,session, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField,FormField,FieldList
import numpy as np
import pandas as pd
from azure.cosmosdb.table.tableservice import TableService
from informatics_classroom.azure_func import init_cosmos,load_answerkey
from informatics_classroom.classroom import classroom_bp
from informatics_classroom.classroom.forms import AnswerForm, ExerciseForm
from informatics_classroom.config import Keys, Config
import informatics_classroom.classroom.helpers as ich
import uuid
import json
import datetime as dt
from markupsafe import escape

# rbb setting for testing without authentication
TESTING_MODE = Config.TESTING
DATABASE = Config.DATABASE
DATABASE = 'bids-class'

ClassGroups=sorted(['PMAP','CDA','FHIR','OHDSI'])

@classroom_bp.context_processor
def inject_roles():
    # returns dictionary of items automatically available in Jinja2 templates
    return {
        'is_admin': is_admin(),
        'is_instructor': is_instructor()
    }

def load_data_from_cosmos(container_name, query, parameters):
    """Load data from Cosmos DB using query and parameters."""
    container = init_cosmos(container_name, DATABASE)
    return list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

# --- DATABASE GETTER ROUTES ---

def get_current_user(user_id = None):
    # update to make sure this is checked to exist
    user_id = user_id if user_id else session['user'].get('preferred_username')
    container = init_cosmos('users', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [{"name": "@user_id", "value": user_id}]
    return list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

def get_token_details(token):

    container = init_cosmos("tokens", DATABASE)
    query = "SELECT * FROM c WHERE c.id = @token"
    parameters = [{"name": "@token", "value": token}]
    result = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
    return result

def get_quiz(class_val, module_val):
    container = init_cosmos("quiz", DATABASE)
    query = "SELECT * FROM c WHERE c.class = @class_val AND c.module = @module_val"
    parameters = [
        {"name": "@class_val", "value": class_val},
        {"name": "@module_val", "value": int(module_val)}
    ]
    result = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
    return result

def get_quiz_by_id(quiz_id):
    container = init_cosmos('quiz', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @quiz_id"
    parameters = [{"name": "@quiz_id", "value": quiz_id}]
    result = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
    return result

# this should be updated to be checked against the current quiz questions
def get_user_answers_for_quiz(class_val, module_val, team):
    answer_container = init_cosmos('answer', DATABASE)
    answer_query = """
        SELECT c.question, c.answer, c.correct FROM c
        WHERE c.PartitionKey = @partition_key AND c.team = @team
        ORDER BY c.datetime DESC
    """
    answer_parameters = [
        {"name": "@partition_key", "value": f"{class_val}_{module_val}"},
        {"name": "@team", "value": team}
    ]
    answers = list(answer_container.query_items(query=answer_query, parameters=answer_parameters, enable_cross_partition_query=True))

    return answers

def get_user_role(user_id = None):
    result = get_current_user(user_id=user_id)
    if result:
        return result[0]['role']

    return None

# get all accessible classes for a user (not owned classes)
def get_classes_for_user(user_id = None, include_owned = 0):

    if include_owned:
        quizzes = get_quizzes_for_user(user_id)
        accessible_classes = list({ quiz["class"] for quiz in quizzes })
        return accessible_classes
    
    users = get_current_user()

    accessible_classes = users[0].get("accessible_classes", [])
    # Fetch available modules for accessible classes
    return accessible_classes

# get all modules for a class
def get_modules_for_class(class_val):
    quiz_container = init_cosmos('quiz', DATABASE)
    query = """
        SELECT DISTINCT c.module FROM c
        WHERE c.class = @class_val
    """
    parameters = [{"name": "@class_val", "value": class_val}]
    modules = [quiz["module"] for quiz in quiz_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True)]
    return modules

# primary quiz access route for gathering all classes a user should have access to
def get_quizzes_for_user(user_id = None, include_answers = 0):

    user_id = session['user'].get('preferred_username') if session['user'] else user_id
    container = init_cosmos('quiz', DATABASE)

    # Combine conditions to filter quizzes by ownership or class access
    if include_answers:
        query = """
            SELECT DISTINCT c.class, c.module, c.questions FROM c
            WHERE c.owner = @user_id
            OR ARRAY_CONTAINS(@accessible_classes, c.class)
        """
    else:
        query = """
            SELECT DISTINCT c.class, c.module FROM c
            WHERE c.owner = @user_id
            OR ARRAY_CONTAINS(@accessible_classes, c.class)
        """
    # Fetch the accessible classes from user data
    accessible_classes = get_classes_for_user(user_id)
    parameters = [
        {"name": "@user_id", "value": user_id},
        {"name": "@accessible_classes", "value": accessible_classes},
    ]

    quizzes = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
    return quizzes

def get_and_validate_token(token):
    token_result = get_token_details(token=token)

    if not token_result:
        message = "Invalid token"
        status_code = 404
        return message, status_code
    
    token_data = token_result[0]
    if dt.datetime.now(dt.timezone.utc) > dt.datetime.fromisoformat(token_data["expiry"]):
        message = "Token has expired"
        status_code = 403
        return message, status_code
    
    return token_data, 200


def set_object(object, table):
    container = init_cosmos(table, DATABASE)
    container.upsert_item(object)

# --- HTML-SERVING ROUTES ---
@classroom_bp.route("/generate-token", methods=["GET"])
def generate_token_page():
    """Render the token generation page."""
    # Make sure the user is logged in
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))

    users = get_current_user()
    if not users:
        return redirect(url_for("auth_bp.login"))

    accessible_classes = get_classes_for_user()

    class_modules = {}
    for class_val in accessible_classes:
        modules = get_modules_for_class(class_val)
        class_modules[class_val] = modules

    return render_template(
        "token_generation.html",
        title="Generate Token",
        user=session.get("user"),
        classes=accessible_classes,
        class_modules=json.dumps(class_modules)  # Pass as JSON
    )



def has_class_access(user_id, class_val):
    accessible_classess = get_classes_for_user(user_id)
    return class_val in accessible_classess

@classroom_bp.route("/create-quiz", methods=["GET"])
def create_quiz_page():
    """Render the create quiz page."""
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))
    return render_template("create_quiz.html", title="Create Quiz")

@classroom_bp.route("/modify-quiz", methods=["GET"])
def modify_quiz_page():
    """Render the modify quiz page."""
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))

    if not (is_instructor() or is_admin()):
        return redirect(url_for("classroom_bp.landingpage"))
    
    return render_template("modify_quiz.html", title="Modify Quiz")

@classroom_bp.route("/submit-answers", methods=["GET"])
def submit_answers_page():
    """Render the submit answers page."""
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))
    return render_template("submit_answers.html", title="Submit Answers")

@classroom_bp.route("/manage-users", methods=["GET"])
def manage_users_page():
    """Render the manage users page."""
    if not ich.check_user_session(session):
    #or not is_admin(session['user']):
        return redirect(url_for("auth_bp.login"))
    return render_template("manage_users.html", title="Manage Users")

@classroom_bp.route("/exercise-review", methods=["GET"])
def exercise_review_page():
    """Render the Exercise Review page."""
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))  # Redirect to login if not authorized
    # Render the HTML with the accessible classes
    return render_template("exercise_review.html", classes=get_classes_for_user(), title="Exercise Review")


# --- API ROUTES ---

@classroom_bp.route("/api/view-quizzes", methods=["GET"])
def view_quizzes():
    """Retrieve quizzes the user has access to."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    # check if user_id has been passed
    if request.args.get("user_id"):
        quizzes = get_quizzes_for_user(user_id=request.args.get("user_id"))
    else:
        quizzes = get_quizzes_for_user()

    return jsonify({"quizzes": quizzes}), 200


@classroom_bp.route("/api/grant-class-permission", methods=["POST"])
def grant_class_permission():
    """Grant class access to a user."""
    if not session.get("user") or not is_admin(session['user']):
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json
    user_id = data.get('user_id')
    class_val = data.get('class_val')

    if not user_id or not class_val:
        return jsonify({"message": "Missing fields"}), 400

    users = get_current_user(user_id=user_id)

    if not users:
        return jsonify({"message": "User not found"}), 404

    user = users[0]
    if 'accessible_classes' not in user:
        user['accessible_classes'] = []

    if class_val not in user['accessible_classes']:
        user['accessible_classes'].append(class_val)

    set_object(user, 'users')
    return jsonify({"message": "Class permission granted successfully"}), 200

@classroom_bp.route("/api/get-quiz", methods=["GET"])
def get_quiz_details():
    """Retrieve quiz details using a token."""
    token = request.args.get("token")
    if not token:
        return jsonify({"message": "Token is required"}), 400

    # Validate the token

    token_data, status_code = get_and_validate_token(token=token)
    if status_code != 200:
        return jsonify({"message": token_data}), status_code

    class_val = token_data["class_val"]
    module_val = token_data.get("module_val")

    # Fetch quiz questions
    result = get_quiz(class_val=class_val, module_val=module_val)
    if not result:
        return jsonify({"message": "Quiz not found"}), 404

    quiz = result[0]
    return jsonify({"questions": quiz.get("questions", [])}), 200

# this route gets quiz answers 
@classroom_bp.route("/api/get-quiz-content", methods=["GET"])
def get_quiz_content():
    """Retrieve the content of a quiz along with submitted answers."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    class_val = request.args.get("class_val")
    module_val = request.args.get("module_val")
    team = session['user'].get('preferred_username')

    if not class_val or not module_val:
        return jsonify({"message": "Class and module values are required."}), 400

    # Fetch the quiz data
    quizzes = get_quiz(class_val=class_val, module_val=module_val)

    if not quizzes:
        return jsonify({"message": "Quiz not found."}), 404

    quiz = quizzes[0]

    # Fetch submitted answers
    answers = get_user_answers_for_quiz(class_val = class_val, module_val = module_val, team = team)
    # Map the most recent answers per question
    recent_answers = {}
    for answer in answers:
        question_num = answer["question"]
        if question_num not in recent_answers:
            recent_answers[question_num] = {
                "answer": answer["answer"],
                "correct": bool(answer["correct"]),
            }

    trimmed_questions = []

    for q in quiz.get("questions", []):
        trimmed_questions.append({
            "question_num": q.get("question_num")
        })
    return jsonify({
        "title": quiz.get("title"),
        "questions": trimmed_questions,
        "recent_answers": recent_answers
    }), 200

# should depricate/remove
@classroom_bp.route("/api/get-quiz-content-modify", methods=["GET"])
def get_quiz_content_modify():
    """Retrieve questions for a specific quiz."""
    quiz_id = request.args.get("quiz_id")
    if not quiz_id:
        return jsonify({"message": "Quiz ID is required"}), 400

    quizzes = get_quiz_by_id(quiz_id=quiz_id)

    if not quizzes:
        return jsonify({"message": "Quiz not found"}), 404

    quiz = quizzes[0]
    return jsonify({"questions": quiz.get("questions", [])}), 200

@classroom_bp.route("/api/generate-token", methods=["POST"])
def generate_token():
    """Generate a token for a class and module."""
    if not session.get("user"):
        return jsonify({"message": "Unauthorized"}), 401

    user_name = session['user'].get('preferred_username').split('@')[0]
    class_val = request.json.get('class_val')
    module_val = request.json.get('module_val')

    if not class_val or not module_val:
        return jsonify({"message": "Both class_val and module_val are required"}), 400

    if not has_class_access(user_name, class_val):
        return jsonify({"message": "You do not have access to this class"}), 403

    token = str(uuid.uuid4())
    expiry_time = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24)

    token_entry = {
        'id': token,
        'user': user_name,
        'class_val': class_val,
        'module_val': module_val,
        'expiry': expiry_time.isoformat()
    }

    set_object(token_entry, 'tokens')

    return jsonify({"token": token, "expiry": expiry_time.isoformat()}), 201


@classroom_bp.route("/api/create-quiz", methods=["POST"])
def create_quiz():
    """Create a new quiz."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    if not is_admin() or is_instructor():
        return jsonify({"message": "Unauthorized"}), 401
    
    data = request.json
    quiz_title = data.get('quiz_title')
    description = data.get('description')
    class_val = data.get('class')
    module = data.get('module')
    questions = data.get('questions', [])
    created_by = session['user'].get('preferred_username')

    if not quiz_title or not description or not class_val or module is None:
        return jsonify({"message": "Invalid input"}), 400

    # Filter and process valid questions
    processed_questions = []
    for question in questions:
        if isinstance(question, dict):  # Only process valid dictionaries
            question_num = question.get("question_num")
            correct_answer = question.get("correct_answer", "")
            open_flag = question.get("open", "False") == "True"

            if question_num is not None:  # Ensure question_num exists
                processed_questions.append({
                    "question_num": question_num,
                    "correct_answer": correct_answer,
                    "open": open_flag
                })

    if not processed_questions:
        return jsonify({"message": "Invalid input: No valid questions provided"}), 400

    quiz_id = f"{class_val}_{module}"
    quiz = {
        'id': quiz_id,
        'class': class_val,
        'module': module,
        'title': quiz_title,
        'description': description,
        'questions': processed_questions,
        'owner': created_by,
        'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'updated_at': dt.datetime.now(dt.timezone.utc).isoformat()
    }

    set_object(quiz, 'quiz')

    return jsonify({"message": "Quiz created successfully", "quiz_id": quiz_id}), 201

@classroom_bp.route("/api/manage-user", methods=["POST"])
def manage_user():
    """Manage user roles and permissions."""
    if not session.get("user"):
    #or not is_admin(session["user"]):
        return jsonify({"message": "Unauthorized"}), 401


    if not (is_admin() or is_instructor()):
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json

    user_id = data.get("user_id")
    user = get_current_user(user_id = user_id)

    if user:
        user = user[0]
        user_role = user['role']
    else:
        user = dict()
        user["id"] = user_id
        user["userId"] = user_id
        user["full_name"] = ''
        user["email"] = ''
        user["accessible_classes"] = []
        user['role'] = ''
        user_role = ''

    class_val = data.get("class_val")
    role = data.get("role")

    if (role and (role != user_role)):
        user['role'] = role

    if class_val and class_val not in user["accessible_classes"]:
        user["accessible_classes"].append(class_val)

    set_object(user, 'users')

    return jsonify({"message": f"User {user_id} updated successfully"}), 200

# change this so that quizzes are not modified by id
@classroom_bp.route("/api/modify-quiz", methods=["POST"])
def modify_quiz():
    """Update a specific quiz's questions and track changes."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    if not is_admin() or is_instructor():
        return jsonify({"message": "Unauthorized"}), 401
    
    data = request.json
    quiz_id = data.get("quiz_id")
    questions = data.get("questions", [])  # Accepting the entire questions array

    if not quiz_id or not isinstance(questions, list):
        return jsonify({"message": "Missing or invalid required fields"}), 400

    updated_by = session['user'].get('preferred_username')
    update_datetime = str(dt.datetime.now(dt.timezone.utc))

    quizzes = get_quiz_by_id(quiz_id=quiz_id)

    if not quizzes:
        return jsonify({"message": "Quiz not found"}), 404

    quiz = quizzes[0]
    existing_questions = {q["question_num"]: q for q in quiz.get("questions", [])}

    # Track changes
    updated_questions = []
    changes = []

    for idx, question in enumerate(questions, start=1):
        question_num = question.get("question_num", idx)
        correct_answer = question.get("correct_answer", "")
        open_flag = question.get("open", False)

        if question_num in existing_questions:
            original = existing_questions[question_num]
            if original["correct_answer"] != correct_answer or original["open"] != open_flag:
                changes.append({
                    "question_num": question_num,
                    "change_type": "update",
                    "updated_by": updated_by,
                    "update_datetime": update_datetime,
                    "old_value": {
                        "correct_answer": original["correct_answer"],
                        "open": original["open"]
                    },
                    "new_value": {
                        "correct_answer": correct_answer,
                        "open": open_flag
                    }
                })
            updated_questions.append({
                "question_num": question_num,
                "correct_answer": correct_answer,
                "open": open_flag,
                "change_log": original.get("change_log", []) + [changes[-1]] if changes else original.get("change_log", [])
            })
        else:
            changes.append({
                "question_num": question_num,
                "change_type": "add",
                "updated_by": updated_by,
                "update_datetime": update_datetime,
                "new_value": {
                    "correct_answer": correct_answer,
                    "open": open_flag
                }
            })
            updated_questions.append({
                "question_num": question_num,
                "correct_answer": correct_answer,
                "open": open_flag,
                "change_log": [changes[-1]]
            })

    # Detect removed questions
    removed_questions = set(existing_questions.keys()) - {q["question_num"] for q in updated_questions}
    for question_num in removed_questions:
        original = existing_questions[question_num]
        changes.append({
            "question_num": question_num,
            "change_type": "delete",
            "updated_by": updated_by,
            "update_datetime": update_datetime,
            "old_value": {
                "correct_answer": original["correct_answer"],
                "open": original["open"]
            }
        })

    # Finalize the quiz
    quiz["questions"] = updated_questions
    quiz["updated_by"] = updated_by
    quiz["update_datetime"] = update_datetime
    quiz["change_log"] = quiz.get("change_log", []) + changes

    set_object(quiz, 'quiz')

    return jsonify({
        "success": True,
        "message": "Quiz updated successfully",
        "updated_by": updated_by,
        "update_datetime": update_datetime,
        "changes": changes
    }), 200


# Optional: Add a cleanup utility to remove expired tokens periodically
@classroom_bp.route("/cleanup-tokens", methods=["POST"])
def cleanup_tokens():
    container = init_cosmos('tokens', DATABASE)
    query = "SELECT * FROM c"

    tokens = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    current_time = dt.datetime.now(dt.timezone.utc)
    for token in tokens:
        if dt.datetime.fromisoformat(token['expiry']) < current_time:
            container.delete_item(item=token['id'], partition_key=token['id'])

    return jsonify({"message": "Expired tokens cleaned up."}), 200

# User Role Management
@classroom_bp.route("/assign-role", methods=["POST"])
def assign_role():
    if not session.get("user") or not is_admin(session['user']):
        return jsonify({"message": "Unauthorized"}), 401

    if not is_admin() or is_instructor():
        return jsonify({"message": "Unauthorized"}), 401
    
    data = request.json
    user_id = data.get('user_id')
    role = data.get('role')
    full_name = data.get('full_name')
    email = data.get('email')
    additional_info = data.get('additional_info', {})

    if not user_id or role not in ['Admin', 'Instructor', 'Student'] or not full_name or not email:
        return jsonify({"message": "Invalid input"}), 400

    user = {
        'id': user_id,
        'role': role,
        'full_name': full_name,
        'email': email,
        'additional_info': additional_info,
        'created_at': dt.datetime.now(dt.timezone.utc).isoformat()
    }

    set_object(user, 'users')

    return jsonify({"message": f"Role {role} assigned to {user_id}"}), 200

# Check user role
# this doesn't seem to handle anything about the user role
@classroom_bp.route("/check-role", methods=["GET"])
def check_role():

    user_id = request.args.get("user_id")

    result = get_user_role(user_id=user_id)

    if not result[0]['role']:
        return jsonify({"message": "User role not found"}), 404

    return jsonify(result[0]), 200

# Permissions Middleware
def is_admin(user=None):
    if get_user_role(user_id=user) == 'Admin':
        return True
    return False

def is_instructor(user=None):
    if get_user_role(user_id=user) == 'Instructor':
        return True
    return False

def is_student(user):
    if get_user_role(user_id=user) == 'Student':
        return True
    return False

@classroom_bp.route('/home')
def landingpage():
    return render_template('home.html',title='Home')

@classroom_bp.route("/quiz",methods=['GET','POST'])
def quiz():
    return render_template('quiz.html')

@classroom_bp.route("/api/get-session-quizzes", methods=["GET"])
def get_session_quizzes():
    """Retrieve quizzes available to the user via session."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    quizzes = get_quizzes_for_user()
    return jsonify({"quizzes": quizzes}), 200

def process_answers(token, answers):
    """Validate and store multiple answers."""
    # Validate token
    token_data, status_code = get_and_validate_token(token=token)
    if status_code != 200:
        return jsonify({"message": token_data}), status_code

    class_val = token_data["class_val"]
    module_val = token_data.get("module_val")
    team = token_data.get("user")

    # Fetch all questions for the quiz in a single query
    container = init_cosmos('quiz', DATABASE)
    query = """
        SELECT c.question_num, c.correct_answer FROM quiz q
        JOIN c IN q.questions
        WHERE q.class = @class_val AND q.module = @module_val
    """
    parameters = [
        {"name": "@class_val", "value": class_val},
        {"name": "@module_val", "value": int(module_val)},
    ]
    questions = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    if not questions:
        return {"message": "Quiz not found", "status": 404, "feedback": {}}

    # Create a lookup for correct answers
    correct_answers = {str(q["question_num"]): str(q["correct_answer"]) for q in questions}

    # Validate and log answers
    feedback = {}
    attempts = []
    for question_num, answer_num in answers.items():
        correct_answer = correct_answers.get(str(question_num))
        if correct_answer is None:
            feedback[question_num] = {"correct": False, "message": "Invalid question number"}
            continue

        is_correct = str(correct_answer) == str(answer_num)
        feedback[question_num] = {"correct": is_correct}

        attempts.append({
            'PartitionKey': f"{class_val}_{module_val}",
            'id': str(uuid.uuid4()),
            'course': class_val,
            'module': module_val,
            'team': team,
            'question': question_num,
            'answer': answer_num,
            'datetime': str(dt.datetime.now(dt.timezone.utc)),
            'correct': int(is_correct),
        })

    # Batch log attempts
    answer_container = init_cosmos('answer', DATABASE)
    for attempt in attempts:
        answer_container.upsert_item(attempt)

    return {"message": "Processed successfully", "status": 200, "feedback": feedback}

def process_answers_session(class_val, module_val, team, answers):
    """Validate and store multiple answers based on session access."""
    # Fetch all questions for the quiz
    container = init_cosmos('quiz', DATABASE)
    query = """
        SELECT c.question_num, c.correct_answer FROM quiz q
        JOIN c IN q.questions
        WHERE q.class = @class_val AND q.module = @module_val
    """
    parameters = [
        {"name": "@class_val", "value": class_val},
        {"name": "@module_val", "value": int(module_val)},
    ]
    questions = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    if not questions:
        return {"message": "Quiz not found", "status": 404, "feedback": {}}

    # Create a lookup for correct answers
    correct_answers = {str(q["question_num"]): str(q["correct_answer"]) for q in questions}

    # Validate and log answers
    feedback = {}
    attempts = []
    for question_num, answer_num in answers.items():
        correct_answer = correct_answers.get(str(question_num))
        if correct_answer is None:
            feedback[question_num] = {"correct": False, "message": "Invalid question number"}
            continue

        is_correct = str(correct_answer) == str(answer_num)
        feedback[question_num] = {"correct": is_correct}

        attempts.append({
            'PartitionKey': f"{class_val}_{module_val}",
            'id': str(uuid.uuid4()),
            'course': class_val,
            'module': module_val,
            'team': team,
            'question': question_num,
            'answer': answer_num,
            'datetime': str(dt.datetime.now(dt.timezone.utc)),
            'correct': int(is_correct),
        })

    # Batch log attempts
    answer_container = init_cosmos('answer', DATABASE)
    for attempt in attempts:
        answer_container.upsert_item(attempt)

    return {"message": "Processed successfully", "status": 200, "feedback": feedback}

@classroom_bp.route("/submit-answer", methods=['POST'])
def submit_answer():
    """Handle submission of a single answer."""
    token = request.form.get("token")  # Optional for token-based submissions
    team = session['user'].get('preferred_username') if session.get('user') else None
    question_num = request.form.get("question_num")
    answer_num = request.form.get("answer_num")
    class_val = request.form.get("class_val") if request.form.get("class_val") else request.form.get("class")  # New for session-based submissions
    module_val = request.form.get("module_val") if request.form.get("module_val") else request.form.get("module") # New for session-based submissions

    if not all([team, question_num, answer_num]) and (not token and not (class_val and module_val)):
        return jsonify({"message": "Missing required fields"}), 400

    if token:
        # Token-based processing
        message, status_code = get_and_validate_token(token=token)
        if status_code != 200:
            return jsonify({
                "message" : message, 
                "correct" : False,
                "success" : False
            }), 401
        result = process_answers(token, {question_num: answer_num})
    else:
        # Session-based processing
        result = process_answers_session(class_val, module_val, team, {question_num: answer_num})

    feedback = result["feedback"].get(question_num, {})
    return jsonify({
        "message": feedback.get("message", "Processed successfully"),
        "correct": feedback.get("correct", False),
        "success" : True
    }), result["status"]
    #return str(feedback.get("correct", False)), 200

@classroom_bp.route("/api/submit-answers", methods=["POST"])
def submit_answers():
    """Submit multiple answers for a quiz."""
    data = request.json

    token = data.get("token")
    team = session['user'].get('preferred_username')
    answers = data.get("answers", {})

    if not token or not team:
        return jsonify({"message": "Token and team are required"}), 400

    if not answers:
        return jsonify({"message": "No answers provided"}), 400

    result = process_answers(token, answers)
    feedback = result["feedback"]
    correct_count = sum(1 for response in feedback.values() if response.get("correct", False))
    total_questions = len(answers)

    return jsonify({
        "message": f"Submission complete. Score: {correct_count}/{total_questions}",
        "feedback": feedback,
    }), result["status"]

@classroom_bp.route("/assignment", methods=["GET"])
def assignment():
    """Render the assignment analysis page with class selection."""
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))

    accessible_classes = get_classes_for_user()

    # Validate accessible_classes is a list
    if not isinstance(accessible_classes, list):
        accessible_classes = []

    return render_template("assignment.html", classes=accessible_classes, title="Assignment Analysis")

@classroom_bp.route("/api/get-modules", methods=["GET"])
def get_modules(include_owned = 0):
    """Retrieve modules for a specific class."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    class_val = request.args.get("class_name")
    if not class_val:
        return jsonify({"message": "Class value is required."}), 400

    accessible_classes = get_classes_for_user(include_owned=include_owned)
    if class_val not in accessible_classes:
        return jsonify({"message": f"You do not have access to class {class_val}."}), 403

    # Fetch modules for the accessible class
    modules = get_modules_for_class(class_val)
    
    return jsonify({"modules": modules}), 200

@classroom_bp.route("/api/analyze-assignment", methods=["POST"])
def analyze_assignment():
    """Analyze the selected class and module with layered breakdowns."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    if not is_admin() or is_instructor():
        return jsonify({"message": "Unauthorized"}), 401
    
    data = request.json

    class_name = escape(data.get("class_name", "").strip().lower())
    module_number = data.get("module_number", "").strip()

    if not class_name or not module_number:
        return jsonify({"message": "Class and module are required."}), 400

    try:
        module_number = int(module_number)
    except ValueError:
        return jsonify({"message": "Module must be a valid number."}), 400

    quiz = get_quiz(class_val=class_name, module_val=module_number)
    
    if not quiz:
        return jsonify({"message": f"No quiz found for class {class_name} and module {module_number}."}), 404

    active_questions = {str(q["question_num"]) for q in quiz[0].get("questions", [])}

    container = init_cosmos('answer', DATABASE)
    query = """
        SELECT 
            c.team, 
            c.question, 
            c.answer, 
            c.correct, 
            c.module, 
            c.datetime 
        FROM c 
        WHERE LOWER(c.course) = LOWER(@class_name) AND c.module = @module_number
    """
    parameters = [
        {"name": "@class_name", "value": class_name},
        {"name": "@module_number", "value": str(module_number)}
    ]
    items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    if not items:
        return jsonify({"message": f"No answer data found for class {class_name} and module {module_number}."}), 404

    df = pd.DataFrame(items)

    # Handle datetime only if it exists
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df["datetime"] = df["datetime"].apply(lambda x: x.strftime('%Y-%m-%dT%H:%M:%S') if pd.notnull(x) else None)
    else:
        df["datetime"] = None

    df = df[df["question"].isin(active_questions)]

    # Ensure % correct counts only one correct answer per student
    df["unique_correct"] = df.groupby(["question", "team"])["correct"].transform("max")

    # Calculate unique students who answered correctly
    correct_students = df[df["correct"] == 1].groupby("question")["team"].nunique()

    # Calculate total unique students who attempted the question
    total_students = df.groupby("question")["team"].nunique()

    # Calculate attempt counts for each question
    attempt_count = df.groupby("question")["answer"].count()

    # Combine results into a DataFrame
    question_summary = pd.DataFrame({
        "correct_students": correct_students,
        "total_students": total_students,
        "attempt_count": attempt_count
    }).reset_index()

    # Fill NaN values to ensure no division errors
    question_summary["correct_students"] = question_summary["correct_students"].fillna(0)
    question_summary["total_students"] = question_summary["total_students"].fillna(0)
    question_summary["attempt_count"] = question_summary["attempt_count"].fillna(0)

    # Calculate percent correct
    question_summary["percent_correct"] = round(
        (question_summary["correct_students"] / question_summary["total_students"].replace(0, np.nan)) * 100, 2
    ).fillna(0)  # Set percent_correct to 0 if no students attempted the question

    # Calculate average attempts per student
    question_summary["avg_attempts"] = round(
        question_summary["attempt_count"] / question_summary["total_students"].replace(0, np.nan), 2
    ).fillna(0)

    student_attempts = df.groupby(["question", "team"]).agg(
        attempts=("answer", "count"),
        correct=("unique_correct", "max")
    ).reset_index()

    # Collect all attempts for each student under each question
    attempt_details = {}
    for question, group in df.groupby("question"):
        attempt_details[question] = {
            team: group[group["team"] == team][["answer", "correct", "datetime"]].to_dict(orient="records")
            for team in group["team"].unique()
        }

    question_summary["student_breakdown"] = question_summary["question"].map(
        lambda q: student_attempts[student_attempts["question"] == q].to_dict(orient="records")
    )
    question_summary["details"] = question_summary["question"].map(attempt_details)

    return jsonify({
        "module_summary": question_summary.to_dict(orient="records")
    }), 200

@classroom_bp.route("/api/exercise-review", methods=["GET"])
def exercise_review():
    """Retrieve progress data for classes the user has access to."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    # Fetch accessible quizzes from /api/view-quizzes logic
    quizzes = get_quizzes_for_user(include_answers = 1)

    if not quizzes:
        return jsonify({"message": "No quizzes found."}), 404

    answer_container = init_cosmos('answer', DATABASE)

    # Aggregate progress data for each class
    progress_data = {}

    for quiz in quizzes:
        class_name = quiz.get("class")
        module = quiz.get("module", "Unknown")
        questions = quiz.get("questions", [])
        partition_key = f"{class_name}_{module}"
        # Create a set of active question numbers
        active_questions = {str(q["question_num"]) for q in questions}

        # Fetch answers for the corresponding quiz
        answer_query = """
            SELECT c.question, c.correct FROM c
            WHERE c.PartitionKey = @partition_key AND c.team = @user_id
        """
        answer_parameters = [
            {"name": "@partition_key", "value": partition_key},
            {"name": "@user_id", "value": session['user'].get('preferred_username')}
            ]
        answers = list(answer_container.query_items(
            query=answer_query, parameters=answer_parameters, enable_cross_partition_query=True
        ))

        # Filter answers to include only active questions
        filtered_answers = [a for a in answers if str(a["question"]) in active_questions]
        questions_attempted = {a["question"] for a in filtered_answers}
        correct_questions = {a["question"] for a in filtered_answers if a.get("correct", 0) == 1}

        total_questions = len(active_questions)
        num_attempted = len(questions_attempted)
        num_correct = len(correct_questions)

        if class_name not in progress_data:
            progress_data[class_name] = {
                "class": class_name,
                "overall_progress": 0,
                "overall_correctness": 0,
                "modules": {},
                "total_questions": 0,
                "questions_attempted": 0,
                "questions_correct": 0
            }

        # Add module data
        if module not in progress_data[class_name]["modules"]:
            progress_data[class_name]["modules"][module] = {
                "module": module,
                "total_questions": 0,
                "questions_attempted": 0,
                "questions_correct": 0
            }

        progress_data[class_name]["modules"][module]["total_questions"] += total_questions
        progress_data[class_name]["modules"][module]["questions_attempted"] += num_attempted
        progress_data[class_name]["modules"][module]["questions_correct"] += num_correct

        progress_data[class_name]["total_questions"] += total_questions
        progress_data[class_name]["questions_attempted"] += num_attempted
        progress_data[class_name]["questions_correct"] += num_correct

    # Calculate overall progress and correctness
    for class_data in progress_data.values():
        total_questions = class_data["total_questions"]
        total_questions_attempted = class_data["questions_attempted"]
        total_questions_correct = class_data["questions_correct"]

        class_data["overall_progress"] = round((total_questions_attempted / total_questions) * 100, 2) if total_questions else 0
        class_data["overall_correctness"] = round((total_questions_correct / total_questions_attempted) * 100, 2) if total_questions_attempted else 0

        # Convert modules dictionary to a list
        for module_data in class_data["modules"].values():
            module_data["module_progress"] = round((module_data["questions_attempted"] / module_data["total_questions"]) * 100, 2) if module_data["total_questions"] else 0
            module_data["module_correctness"] = round((module_data["questions_correct"] / module_data["questions_attempted"]) * 100, 2) if module_data["questions_attempted"] else 0

        class_data["modules"] = list(class_data["modules"].values())

    return jsonify(list(progress_data.values())), 200