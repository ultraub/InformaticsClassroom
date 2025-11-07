from flask import render_template,request, jsonify,session, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField,FormField,FieldList
import numpy as np
import pandas as pd
# Cosmos DB imports removed - now using database adapter
# from azure.cosmosdb.table.tableservice import TableService
# from informatics_classroom.azure_func import init_cosmos,load_answerkey
from informatics_classroom.classroom import classroom_bp
from informatics_classroom.classroom.forms import AnswerForm, ExerciseForm
from informatics_classroom.config import Keys, Config
import informatics_classroom.classroom.helpers as ich
import uuid
import json
import datetime as dt
from markupsafe import escape
import requests
from flask import flash

# Database adapter for PostgreSQL/Cosmos DB abstraction
from informatics_classroom.database.factory import get_database_adapter

# rbb setting for testing without authentication
TESTING_MODE = Config.TESTING
DATABASE = Config.DATABASE

ClassGroups=sorted(['PMAP','CDA','FHIR','OHDSI'])

@classroom_bp.context_processor
def inject_roles():
    # returns dictionary of items automatically available in Jinja2 templates
    return {
        'is_admin': is_admin(),
        'is_instructor': is_instructor()
    }

# --- DATABASE GETTER ROUTES ---

def get_current_user(user_id = None):
    # update to make sure this is checked to exist
    user_id = user_id if user_id else session['user'].get('preferred_username').split('@')[0]

    # Use database adapter (works with both PostgreSQL and Cosmos DB)
    db = get_database_adapter()
    users = db.query('users', filters={'id': user_id})
    return users if users else []

def get_token_details(token):
    db = get_database_adapter()
    result = db.query('tokens', filters={'id': token})
    return result

def get_quiz(class_val, module_val):
    db = get_database_adapter()
    result = db.query('quiz', filters={'class': class_val, 'module': int(module_val)})
    return result

def get_quiz_by_id(quiz_id):
    db = get_database_adapter()
    quiz = db.get('quiz', quiz_id)
    return [quiz] if quiz else []

# this should be updated to be checked against the current quiz questions
def get_user_answers_for_quiz(class_val, module_val, team):
    db = get_database_adapter()
    # Use query_raw for complex queries with ORDER BY
    # Note: PostgreSQL stores data in JSONB, so we extract fields using ->> operator
    # Use course/module fields instead of PartitionKey for database-agnostic compatibility
    query = """
        SELECT
            data->>'question' as question,
            data->>'answer' as answer,
            (data->>'correct')::integer as correct
        FROM answer
        WHERE data->>'course' = $1
          AND data->>'module' = $2
          AND data->>'team' = $3
          AND data->>'datetime' IS NOT NULL
        ORDER BY data->>'datetime' DESC
    """
    parameters = [
        {"name": "$1", "value": class_val},
        {"name": "$2", "value": str(module_val)},
        {"name": "$3", "value": team}
    ]
    answers = db.query_raw('answer', query, parameters)
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

    users = get_current_user(user_id)

    if not users or len(users) == 0:
        return []

    user = users[0]
    accessible_classes = []

    # Get classes from new class_memberships structure ONLY
    # We migrated away from accessible_classes for security reasons
    class_memberships = user.get("class_memberships", [])
    if class_memberships:
        accessible_classes = [membership.get("class_id") for membership in class_memberships if membership.get("class_id")]

    return accessible_classes

# get all modules for a class
def get_modules_for_class(class_val):
    db = get_database_adapter()
    # Use query_raw for DISTINCT queries with JSONB syntax
    query = "SELECT DISTINCT (data->>'module')::int as module FROM quiz WHERE data->>'class' = $1 ORDER BY module"
    parameters = [{"name": "$1", "value": class_val}]
    results = db.query_raw('quiz', query, parameters)
    modules = [quiz["module"] for quiz in results]
    return modules

# primary quiz access route for gathering all classes a user should have access to
def get_quizzes_for_user(user_id = None, include_answers = 0):
    user_id = session['user'].get('preferred_username').split('@')[0] if session['user'] else user_id
    db = get_database_adapter()

    # Fetch the accessible classes from user data
    accessible_classes = get_classes_for_user(user_id)

    # For PostgreSQL, use ANY for array containment with JSONB syntax
    # Combine conditions to filter quizzes by ownership or class access
    if include_answers:
        query = """
            SELECT DISTINCT
                data->>'class' as class,
                (data->>'module')::int as module,
                data->'questions' as questions
            FROM quiz
            WHERE data->>'owner' = $1 OR data->>'class' = ANY($2::text[])
        """
    else:
        query = """
            SELECT DISTINCT
                data->>'class' as class,
                (data->>'module')::int as module
            FROM quiz
            WHERE data->>'owner' = $1 OR data->>'class' = ANY($2::text[])
        """

    parameters = [
        {"name": "$1", "value": user_id},
        {"name": "$2", "value": accessible_classes},
    ]

    quizzes = db.query_raw('quiz', query, parameters)
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
    db = get_database_adapter()
    db.upsert(table, object)

# --- HTML-SERVING ROUTES ---
@classroom_bp.route("/generate-token", methods=["GET"])
def generate_token_page():
    """Render the token generation page."""
    # Make sure the user is logged in
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))

    # SECURITY: Only admins and instructors can generate tokens
    if not (is_admin() or is_instructor()):
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("classroom_bp.landingpage"))

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
        return redirect(url_for("auth_bp.login"))

    # SECURITY: Only admins can manage users
    if not is_admin():
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("classroom_bp.landingpage"))

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
    # SECURITY FIX: Corrected parameter passing - is_admin() gets user from session
    if not session.get("user") or not is_admin():
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
    team = session['user'].get('preferred_username').split('@')[0]

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
        question_num = str(answer["question"])  # Force it to a string

        if question_num in recent_answers.keys():
            continue
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

    if not (is_admin() or is_instructor()):
        return jsonify({"message": "Unauthorized"}), 401
    
    data = request.json
    quiz_title = data.get('quiz_title')
    description = data.get('description')
    class_val = data.get('class')
    module = data.get('module')
    questions = data.get('questions', [])
    created_by = session['user'].get('preferred_username').split('@')[0]

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

    if not (is_admin() or is_instructor()):
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json
    quiz_id = data.get("quiz_id")
    questions = data.get("questions", [])  # Accepting the entire questions array

    if not quiz_id or not isinstance(questions, list):
        return jsonify({"message": "Missing or invalid required fields"}), 400

    # SECURITY: Verify quiz ownership before allowing modification
    if not can_modify_quiz(quiz_id):
        return jsonify({"message": "Unauthorized: You do not own this quiz"}), 403

    updated_by = session['user'].get('preferred_username').split('@')[0]
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
            original["open"] = original["open"] if "open" in original.keys() else False
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
    db = get_database_adapter()
    tokens = db.query('tokens')

    current_time = dt.datetime.now(dt.timezone.utc)
    expired_token_ids = []
    for token in tokens:
        if dt.datetime.fromisoformat(token['expiry']) < current_time:
            expired_token_ids.append(token['id'])

    if expired_token_ids:
        db.bulk_delete('tokens', expired_token_ids)

    return jsonify({"message": "Expired tokens cleaned up."}), 200

# User Role Management
@classroom_bp.route("/assign-role", methods=["POST"])
def assign_role():
    # SECURITY FIX: Only admins can assign roles, removed redundant checks
    if not session.get("user") or not is_admin():
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

def owns_quiz(quiz_id, user_id=None):
    """Check if the user owns the specified quiz."""
    if not user_id:
        user_id = session['user'].get('preferred_username').split('@')[0]

    quizzes = get_quiz_by_id(quiz_id=quiz_id)
    if not quizzes:
        return False

    quiz = quizzes[0]
    return quiz.get('owner') == user_id

def can_modify_quiz(quiz_id, user_id=None):
    """Check if the user can modify the specified quiz (admin or owner)."""
    if is_admin(user_id):
        return True
    return owns_quiz(quiz_id, user_id)

@classroom_bp.route('/home')
def landingpage():
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))
    
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
    db = get_database_adapter()
    # For PostgreSQL, use jsonb_array_elements to unnest the questions array
    query = """
        SELECT (q->>'question_num')::int as question_num,
               q->>'correct_answer' as correct_answer,
               (q->>'open')::boolean as open
        FROM quiz, jsonb_array_elements(data->'questions') as q
        WHERE data->>'class' = $1 AND (data->>'module')::int = $2
    """
    parameters = [
        {"name": "$1", "value": class_val},
        {"name": "$2", "value": int(module_val)},
    ]
    questions = db.query_raw('quiz', query, parameters)

    if not questions:
        return {"message": "Quiz not found", "status": 404, "feedback": {}}

    # Create a lookup for correct answers
    correct_answers = {str(q["question_num"]): str(q["correct_answer"]) for q in questions}
    open_answers = {str(q["question_num"]): bool(q["open"]) for q in questions}

    # Validate and log answers
    feedback = {}
    attempts = []
    for question_num, answer_num in answers.items():
        correct_answer = correct_answers.get(str(question_num))

        if open_answers.get(str(question_num)):
            is_correct = True
            feedback[question_num] = {"correct": is_correct}

        elif correct_answer is None:
            feedback[question_num] = {"correct": False, "message": "Invalid question number"}
            continue

        else:
            is_correct = str(correct_answer) == str(answer_num)
            feedback[question_num] = {"correct": is_correct}

        attempts.append({
            'PartitionKey': f"{class_val}_{module_val}",
            'id': str(uuid.uuid4()),
            'course': class_val,
            'module': module_val,
            'team': team,
            'question': question_num,
            'open': open_answers.get(str(question_num)),
            'answer': answer_num,
            'datetime': str(dt.datetime.now(dt.timezone.utc)),
            'correct': int(is_correct),
        })

    # Batch log attempts
    if attempts:
        db = get_database_adapter()
        for attempt in attempts:
            db.upsert('answer', attempt)

    return {"message": "Processed successfully", "status": 200, "feedback": feedback}

def process_answers_session(class_val, module_val, team, answers):
    """Validate and store multiple answers based on session access."""
    # Fetch all questions for the quiz
    db = get_database_adapter()
    # For PostgreSQL, use jsonb_array_elements to unnest the questions array
    query = """
        SELECT (q->>'question_num')::int as question_num,
               q->>'correct_answer' as correct_answer,
               (q->>'open')::boolean as open
        FROM quiz, jsonb_array_elements(data->'questions') as q
        WHERE data->>'class' = $1 AND (data->>'module')::int = $2
    """
    parameters = [
        {"name": "$1", "value": class_val},
        {"name": "$2", "value": int(module_val)},
    ]
    questions = db.query_raw('quiz', query, parameters)

    if not questions:
        return {"message": "Quiz not found", "status": 404, "feedback": {}}

    # Create a lookup for correct answers
    correct_answers = {str(q["question_num"]): str(q["correct_answer"]) for q in questions}
    open_answers = {str(q["question_num"]): bool(q["open"]) for q in questions}
    # Validate and log answers
    feedback = {}
    attempts = []
    for question_num, answer_num in answers.items():
        correct_answer = correct_answers.get(str(question_num))
        
        if open_answers.get(str(question_num)):
            is_correct = True
            feedback[question_num] = {"correct": is_correct}

        elif correct_answer is None:
            feedback[question_num] = {"correct": False, "message": "Invalid question number"}
            continue

        else:
            is_correct = str(correct_answer) == str(answer_num)
            feedback[question_num] = {"correct": is_correct}

        attempts.append({
            'PartitionKey': f"{class_val}_{module_val}",
            'id': str(uuid.uuid4()),
            'course': class_val,
            'module': module_val,
            'team': team,
            'question': question_num,
            'open': open_answers.get(str(question_num)),
            'answer': answer_num,
            'datetime': str(dt.datetime.now(dt.timezone.utc)),
            'correct': int(is_correct),
        })

    # Batch log attempts
    if attempts:
        db = get_database_adapter()
        for attempt in attempts:
            db.upsert('answer', attempt)

    return {"message": "Processed successfully", "status": 200, "feedback": feedback}

@classroom_bp.route("/submit-answer", methods=['POST'])
def submit_answer():
    """Handle submission of a single answer."""
    token = request.form.get("token")  # Optional for token-based submissions
    team = session['user'].get('preferred_username').split('@')[0] if session.get('user') else request.form.get("team")
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
    team = session['user'].get('preferred_username').split('@')[0]
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

    # SECURITY: Only admins and instructors can access assignment analysis
    if not (is_admin() or is_instructor()):
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("classroom_bp.landingpage"))

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
    """Analyze the selected class and module with layered breakdowns,
       plus pivot tables for overall correctness & attempts."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    if not (is_admin() or is_instructor()):
        return jsonify({"message": "Unauthorized"}), 401
    
    data = request.json or {}
    class_name = escape(data.get("class_name", "").strip().lower())
    module_number = data.get("module_number", "").strip()
    year_filter = data.get("year_filter", "").strip()  # e.g. "2025" or ""

    # (basic validations for class_name, module_number)...

    # if we have quiz definitions, do that logic
    quiz = get_quiz(class_val=class_name, module_val=module_number)
    if not quiz:
        return jsonify({
            "message": f"No quiz found for class {class_name} and module {module_number}."
        }), 404

    active_questions = {str(q["question_num"]) for q in quiz[0].get("questions", [])}

    # Query database
    db = get_database_adapter()
    query = """
        SELECT
            data->>'team' as team,
            data->>'question' as question,
            data->>'answer' as answer,
            data->>'correct' as correct,
            data->>'module' as module,
            data->>'datetime' as datetime
        FROM answer
        WHERE LOWER(data->>'course') = LOWER($1) AND data->>'module' = $2 AND data->>'datetime' IS NOT NULL
        ORDER BY data->>'datetime' DESC
    """
    params = [
        {"name": "$1", "value": class_name},
        {"name": "$2", "value": str(module_number)}
    ]
    items = db.query_raw('answer', query, params)
    if not items:
        return jsonify({
            "message": f"No answer data found for class {class_name} and module {module_number}."
        }), 404

    df = pd.DataFrame(items)

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
    # Now df["datetime"] is datetime64[ns, UTC] for all rows.

    # If you need naive datetimes (no tz), you can do:
    df["datetime"] = df["datetime"].dt.tz_convert(None)
    df["question"] = df["question"].astype(str)

    # Drop rows where datetime is NaT
    df = df.dropna(subset=["datetime"])

    # If you have a year filter:
    if year_filter:
        try:
            year_val = int(year_filter)
            df = df[df["datetime"].dt.year == year_val]
        except ValueError:
            pass  # If parsing fails, do nothing or handle differently

    if df.empty:
        return jsonify({
            "message": f"No answer data found for class {class_name}, module {module_number}, year {year_filter}."
        }), 404

    # Then proceed with the rest of your logic:
    df = df[df["question"].isin(active_questions)]

    df["team"] = df["team"].fillna("UnknownTeam").astype(str)
    df["question"] = df["question"].fillna("UnknownQuestion").astype(str)

    # Mark if correct for each (question, team)
    df["unique_correct"] = df.groupby(["question", "team"])["correct"].transform("max")

    # question-level stats
    correct_students = df[df["correct"] == 1].groupby("question")["team"].nunique()
    total_students = df.groupby("question")["team"].nunique()
    attempt_count = df.groupby("question")["answer"].count()

    question_summary = pd.DataFrame({
        "question": correct_students.index,
        "correct_students": correct_students.values
    }).merge(
        total_students.rename("total_students").reset_index(),
        on="question", how="outer"
    ).merge(
        attempt_count.rename("attempt_count").reset_index(),
        on="question", how="outer"
    ).fillna(0)

    question_summary["percent_correct"] = (
        question_summary["correct_students"] / question_summary["total_students"].replace(0, np.nan) * 100
    ).fillna(0).round(2)

    question_summary["avg_attempts"] = (
        question_summary["attempt_count"] / question_summary["total_students"].replace(0, np.nan)
    ).fillna(0).round(2)

    # Build student breakdown
    student_attempts = df.groupby(["question","team"], as_index=False).agg(
        attempts=("answer", "count"),
        correct=("unique_correct", "max")
    )

    # Build attempt details
    #   attempt_details = { question -> { team -> [ {answer, correct, datetime}, ... ] } }
    attempt_details = {}
    for q_val, sub_q in df.groupby("question"):
        attempt_details[q_val] = {}
        for t_val, sub_t in sub_q.groupby("team"):
            attempt_details[q_val][t_val] = sub_t[["answer","correct","datetime"]] \
                .sort_values("datetime", na_position="first") \
                .to_dict(orient="records")

    # Attach student breakdown & details
    def build_student_rows(q):
        return student_attempts[student_attempts["question"] == q].to_dict(orient="records")
    
    question_summary["student_breakdown"] = question_summary["question"].apply(build_student_rows)
    question_summary["details"] = question_summary["question"].apply(lambda q: attempt_details.get(q, {}))

    # ------------------------------------------
    # Build the pivot tables for DataTables
    # ------------------------------------------

    # 1) Correctness pivot
    #    For each (team, question), take max(correct). 0 or 1.
    df_correct = df.groupby(["team", "question"], as_index=False)["correct"].max()

    pivot_correct = df_correct.pivot_table(
        index="team",
        columns="question",
        values="correct",
        fill_value=0
    ).reset_index()

    # We only want to keep the 'team' column plus question columns in ascending numeric order.
    # Suppose your questions are numeric strings like "1", "2", "3"...
    # Convert them to int for sorting; then reorder columns accordingly.
    all_columns = list(pivot_correct.columns)  # e.g. ['team', '1', '2', '10']
    question_cols = [c for c in all_columns if c != "team"]
    # Sort by integer value (assuming question columns are numeric strings)
    question_cols_sorted = sorted(question_cols, key=lambda x: int(x))

    # Reorder pivot_correct so "team" is first, then question columns
    pivot_correct = pivot_correct[["team"] + question_cols_sorted]

    # Add "percent_correct" = (sum of correct columns) / (number of question cols) * 100
    pivot_correct["percent_correct"] = (
        pivot_correct[question_cols_sorted].sum(axis=1) / len(question_cols_sorted) * 100
    ).round(2)

    # Put that at the far right
    pivot_correct = pivot_correct[["team"] + question_cols_sorted + ["percent_correct"]]

    # Convert to arrays for JSON
    correctness_cols = pivot_correct.columns.tolist()
    correctness_rows = pivot_correct.values.tolist()


    # 2) Attempts pivot
    #    For each (team, question), count how many answers (submissions) they made
    df_attempts = df.groupby(["team", "question"], as_index=False)["answer"].count()

    pivot_attempts = df_attempts.pivot_table(
        index="team",
        columns="question",
        values="answer",
        fill_value=0
    ).reset_index()

    # Again, reorder columns
    all_columns = list(pivot_attempts.columns)  # e.g. ['team', '1', '2', '10']
    question_cols = [c for c in all_columns if c != "team"]
    question_cols_sorted = sorted(question_cols, key=lambda x: int(x))
    pivot_attempts = pivot_attempts[["team"] + question_cols_sorted]

    # Add "avg_attempts" = average across question columns
    pivot_attempts["avg_attempts"] = (
        pivot_attempts[question_cols_sorted].mean(axis=1)
    ).round(2)

    # Put that at the far right
    pivot_attempts = pivot_attempts[["team"] + question_cols_sorted + ["avg_attempts"]]

    # Convert to arrays for JSON
    attempts_cols = pivot_attempts.columns.tolist()
    attempts_rows = pivot_attempts.values.tolist()

    # Finally, return them in your JSON response (along with module_summary)
    return jsonify({
        "module_summary": question_summary.to_dict(orient="records"),
        "table_correctness": {
            "columns": correctness_cols,
            "rows": correctness_rows
        },
        "table_attempts": {
            "columns": attempts_cols,
            "rows": attempts_rows
        }
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

    db = get_database_adapter()

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
            SELECT data->>'question' as question, (data->>'correct')::int as correct
            FROM answer
            WHERE data->>'partition_key' = $1 AND data->>'team' = $2
        """
        answer_parameters = [
            {"name": "$1", "value": partition_key},
            {"name": "$2", "value": session['user'].get('preferred_username').split('@')[0]}
            ]
        answers = db.query_raw('answer', answer_query, answer_parameters)

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


@classroom_bp.route("/fhir", methods=["GET"])
def fhir_page():
    """Render the submit answers page."""
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))
    return render_template("fhir.html", title="FHIR Route")


@classroom_bp.route('/fhir-call', methods=['POST'])
def call_fhir():
    """
    This route receives a JSON payload with a `url` field.
    It uses make_fhir_call to get the data from the FHIR endpoint
    and returns the result as JSON for the AJAX call to display.
    """
    data = request.get_json()
    fhir_url = data['url']

    # Call the function that retrieves FHIR data
    result_str = make_fhir_call(fhir_url)

    # Convert the JSON string result into a Python dict so we can jsonify it properly
    # If you want to return a raw string, you can do so, 
    # but here we convert it back to JSON for a clean JSON response:
    result_json = json.loads(result_str)

    # Return as JSON
    return jsonify(result_json)

def get_access_token():
    url = "https://excite.eastus.cloudapp.azure.com/oauth2/default/token"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "password",
        "user_role": "users",
        "username": "physician",
        "password": "Password123!",
        "client_id": "q8hPK8HZnwUbPraNyilbRZAEwycVN1zfHeQrjGfP9AM",
        "scope": "openid offline_access api:oemr api:fhir api:port user/allergy.read user/allergy.write user/appointment.read user/appointment.write user/dental_issue.read user/dental_issue.write user/document.read user/document.write user/drug.read user/encounter.read user/encounter.write user/facility.read user/facility.write user/immunization.read user/insurance.read user/insurance.write user/insurance_company.read user/insurance_company.write user/insurance_type.read user/list.read user/medical_problem.read user/medical_problem.write user/medication.read user/medication.write user/message.write user/patient.read user/patient.write user/practitioner.read user/practitioner.write user/prescription.read user/procedure.read user/soap_note.read user/soap_note.write user/surgery.read user/surgery.write user/transaction.read user/transaction.write user/vital.read user/vital.write user/AllergyIntolerance.read user/CareTeam.read user/Condition.read user/Coverage.read user/Encounter.read user/Immunization.read user/Location.read user/Medication.read user/MedicationRequest.read user/Observation.read user/Organization.read user/Organization.write user/Patient.read user/Patient.write user/Practitioner.read user/Practitioner.write user/PractitionerRole.read user/Procedure.read patient/encounter.read patient/patient.read patient/AllergyIntolerance.read patient/CareTeam.read patient/Condition.read patient/Coverage.read patient/Encounter.read patient/Immunization.read patient/MedicationRequest.read patient/Observation.read patient/Patient.read patient/Procedure.read system/Patient.$export",
    }

    response = requests.post(url, headers=headers, data=data, timeout=10)
    response.raise_for_status()
    return response.json()['access_token']

def make_fhir_call(fhir_url):
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "accept": "application/json",
    }

    response = requests.get(fhir_url, headers=headers, timeout=10)
    response.raise_for_status()
    # Return raw JSON string (pretty-printed). 
    # You could also return `response.json()` directly if you prefer.
    return json.dumps(response.json(), indent=4)