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
#DATABASE = 'bids-class'

ClassGroups=sorted(['PMAP','CDA','FHIR','OHDSI'])

def load_data_from_cosmos(container_name, query, parameters):
    """Load data from Cosmos DB using query and parameters."""
    container = init_cosmos(container_name, DATABASE)
    return list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

# --- HTML-SERVING ROUTES ---
@classroom_bp.route("/generate-token", methods=["GET"])
def generate_token_page():
    """Render the token generation page."""
    if not ich.check_user_session(session):
        return redirect(url_for("auth_bp.login"))

    user_id = session['user'].get('preferred_username')
    container = init_cosmos('users', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [{"name": "@user_id", "value": user_id}]
    users = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    if not users:
        return redirect(url_for("auth_bp.login"))

    accessible_classes = users[0].get("accessible_classes", [])

    # Fetch available modules for accessible classes
    quizzes_container = init_cosmos('quiz', DATABASE)
    modules_query = "SELECT DISTINCT c.class, c.module FROM c WHERE ARRAY_CONTAINS(@classes, c.class)"
    modules_parameters = [{"name": "@classes", "value": accessible_classes}]
    modules = list(quizzes_container.query_items(query=modules_query, parameters=modules_parameters, enable_cross_partition_query=True))

    # Organize modules by class
    class_modules = {}
    for item in modules:
        if item['class'] not in class_modules:
            class_modules[item['class']] = []
        class_modules[item['class']].append(item['module'])

    return render_template(
        "token_generation.html",
        title="Generate Token",
        user=session.get("user"),
        classes=accessible_classes,
        class_modules=json.dumps(class_modules)  # Serialize class_modules as JSON
    )


def has_class_access(user_id, class_val):
    container = init_cosmos('users', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [{"name": "@user_id", "value": user_id}]
    users = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    if not users:
        return False

    user = users[0]
    return class_val in user.get('accessible_classes', [])

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
# --- API ROUTES ---

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

    container = init_cosmos('users', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [{"name": "@user_id", "value": user_id}]
    users = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    if not users:
        return jsonify({"message": "User not found"}), 404

    user = users[0]
    if 'accessible_classes' not in user:
        user['accessible_classes'] = []

    if class_val not in user['accessible_classes']:
        user['accessible_classes'].append(class_val)

    container.upsert_item(user)
    return jsonify({"message": "Class permission granted successfully"}), 200

@classroom_bp.route("/api/get-quiz", methods=["GET"])
def get_quiz_details():
    """Retrieve quiz details using a token."""
    token = request.args.get("token")
    if not token:
        return jsonify({"message": "Token is required"}), 400

    # Validate the token
    container = init_cosmos("tokens", DATABASE)
    query = "SELECT * FROM c WHERE c.id = @token"
    parameters = [{"name": "@token", "value": token}]
    result = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    if not result:
        return jsonify({"message": "Invalid token"}), 404

    token_data = result[0]
    if dt.datetime.utcnow() > dt.datetime.fromisoformat(token_data["expiry"]):
        return jsonify({"message": "Token has expired"}), 403

    class_val = token_data["class_val"]
    module_val = token_data.get("module_val")

    # Fetch quiz questions
    container = init_cosmos("quiz", DATABASE)
    query = "SELECT * FROM c WHERE c.class = @class_val AND c.module = @module_val"
    parameters = [
        {"name": "@class_val", "value": class_val},
        {"name": "@module_val", "value": int(module_val)}
    ]
    result = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    if not result:
        return jsonify({"message": "Quiz not found"}), 404

    quiz = result[0]
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
    expiry_time = dt.datetime.utcnow() + dt.timedelta(hours=24)

    token_entry = {
        'id': token,
        'user': user_name,
        'class_val': class_val,
        'module_val': module_val,
        'expiry': expiry_time.isoformat()
    }

    container = init_cosmos('tokens', DATABASE)
    container.upsert_item(token_entry)

    return jsonify({"token": token, "expiry": expiry_time.isoformat()}), 201



@classroom_bp.route("/api/create-quiz", methods=["POST"])
def create_quiz():
    """Create a new quiz."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    quiz_title = request.json.get('quiz_title')
    description = request.json.get('description')
    questions = request.json.get('questions', [])
    created_by = session['user'].get('preferred_username')

    if not quiz_title or not description or not questions:
        return jsonify({"message": "Invalid input"}), 400

    container = init_cosmos('quizzes', DATABASE)
    quiz = {
        'id': f"{quiz_title.lower().replace(' ', '_')}",
        'title': quiz_title,
        'description': description,
        'questions': questions,
        'owner': created_by,
        'created_at': dt.datetime.utcnow().isoformat(),
        'updated_at': dt.datetime.utcnow().isoformat()
    }
    container.upsert_item(quiz)
    return jsonify({"message": "Quiz created successfully", "quiz_id": quiz['id']}), 201

@classroom_bp.route("/api/manage-user", methods=["POST"])
def manage_user():
    """Manage user roles and permissions."""
    if not session.get("user"):
    #or not is_admin(session["user"]):
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json
    user_id = data.get("user_id")
    role = data.get("role")
    class_val = data.get("class_val")

    if not user_id or not role:
        return jsonify({"message": "User ID and role are required"}), 400

    container = init_cosmos("users", DATABASE)
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [{"name": "@user_id", "value": user_id}]
    users = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    user = users[0] if users else {"id": user_id, "accessible_classes": []}
    user["role"] = role

    if class_val and class_val not in user["accessible_classes"]:
        user["accessible_classes"].append(class_val)

    container.upsert_item(user)
    return jsonify({"message": f"User {user_id} updated successfully"}), 200

@classroom_bp.route("/api/modify-quiz", methods=["POST"])
def modify_quiz():
    """Modify an existing quiz."""
    if not ich.check_user_session(session):
        return jsonify({"message": "Unauthorized"}), 401

    quiz_id = request.json.get('quiz_id')
    questions = request.json.get('questions', [])
    updated_by = session['user'].get('preferred_username')

    if not quiz_id or not questions:
        return jsonify({"message": "Invalid input"}), 400

    container = init_cosmos('quizzes', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @quiz_id"
    parameters = [{"name": "@quiz_id", "value": quiz_id}]
    result = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    if not result:
        return jsonify({"message": "Quiz not found"}), 404

    quiz = result[0]
    quiz['questions'] = questions
    quiz['updated_at'] = dt.datetime.utcnow().isoformat()
    quiz['updated_by'] = updated_by
    container.upsert_item(quiz)

    return jsonify({"message": "Quiz modified successfully"}), 200
# Optional: Add a cleanup utility to remove expired tokens periodically
@classroom_bp.route("/cleanup-tokens", methods=["POST"])
def cleanup_tokens():
    container = init_cosmos('tokens', DATABASE)
    query = "SELECT * FROM c"

    tokens = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    current_time = dt.datetime.utcnow()
    for token in tokens:
        if dt.datetime.fromisoformat(token['expiry']) < current_time:
            container.delete_item(item=token['id'], partition_key=token['id'])

    return jsonify({"message": "Expired tokens cleaned up."}), 200

# User Role Management
@classroom_bp.route("/assign-role", methods=["POST"])
def assign_role():
    if not session.get("user") or not is_admin(session['user']):
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json
    user_id = data.get('user_id')
    role = data.get('role')
    full_name = data.get('full_name')
    email = data.get('email')
    additional_info = data.get('additional_info', {})

    if not user_id or role not in ['Admin', 'Instructor', 'Student'] or not full_name or not email:
        return jsonify({"message": "Invalid input"}), 400

    container = init_cosmos('users', DATABASE)
    user = {
        'id': user_id,
        'role': role,
        'full_name': full_name,
        'email': email,
        'additional_info': additional_info,
        'created_at': datetime.utcnow().isoformat()
    }
    container.upsert_item(user)

    return jsonify({"message": f"Role {role} assigned to {user_id}"}), 200

# Check user role
@classroom_bp.route("/check-role", methods=["GET"])
def check_role():
    user_id = session.get("user").get('preferred_username')

    container = init_cosmos('users', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [
        {"name": "@user_id", "value": user_id}
    ]

    result = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))

    if not result:
        return jsonify({"message": "User role not found"}), 404

    return jsonify(result[0]), 200

# Permissions Middleware
def is_admin(user):
    container = init_cosmos('users', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [
        {"name": "@user_id", "value": user.get('preferred_username')}
    ]
    result = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))
    if result and result[0]['role'] == 'Admin':
        return True
    return False

def is_instructor(user):
    container = init_cosmos('users', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [
        {"name": "@user_id", "value": user.get('preferred_username')}
    ]
    result = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))
    if result and result[0]['role'] == 'Instructor':
        return True
    return False

def is_student(user):
    container = init_cosmos('users', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [
        {"name": "@user_id", "value": user.get('preferred_username')}
    ]
    result = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))
    if result and result[0]['role'] == 'Student':
        return True
    return False

@classroom_bp.route("/view-quizzes", methods=["GET"])
def view_quizzes():
    if not session.get("user"):
    # or not is_student(session['user']):
        return jsonify({"message": "Unauthorized"}), 401

    # Logic to fetch quizzes accessible to the student
    container = init_cosmos('users', DATABASE)
    query = "SELECT c.accessible_classes FROM c WHERE c.userId = @user_id"
    parameters = [
        {
            "name": "@user_id", 
            "value": session['user'].get('preferred_username')
        }
    ]
    quizzes = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))
    print(json.dumps(quizzes))

    return jsonify({"quizzes": quizzes[0]['accessible_classes']}), 200

@classroom_bp.route('/home')
def landingpage():
    return render_template('home.html',title='Home')

@classroom_bp.route("/quiz",methods=['GET','POST'])
def quiz():
    return render_template('quiz.html')

def process_answers(token, team, answers):
    """Validate and store multiple answers."""
    # Validate token
    container = init_cosmos('tokens', DATABASE)
    query = "SELECT * FROM c WHERE c.id = @token"
    parameters = [{"name": "@token", "value": token}]
    result = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
    
    if not result or not isinstance(result[0], dict):
        return {"message": "Invalid token", "status": 404, "feedback": {}}

    token_data = result[0]
    class_val = token_data.get("class_val")
    module_val = token_data.get("module_val")

    if not class_val or module_val is None:
        return {"message": "Invalid class or module in token", "status": 400, "feedback": {}}

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
            'datetime': str(dt.datetime.utcnow()),
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
    token = request.form.get("token")
    team = request.form.get("team")
    question_num = request.form.get("question_num")
    answer_num = request.form.get("answer_num")

    if not all([token, team, question_num, answer_num]):
        return jsonify({"message": "Missing required fields"}), 400

    result = process_answers(token, team, {question_num: answer_num})
    feedback = result["feedback"].get(question_num, {})
    return jsonify({
        "message": feedback.get("message", "Processed successfully"),
        "correct": feedback.get("correct", False),
    }), result["status"]




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

    result = process_answers(token, team, answers)
    feedback = result["feedback"]
    correct_count = sum(1 for response in feedback.values() if response.get("correct", False))
    total_questions = len(answers)

    return jsonify({
        "message": f"Submission complete. Score: {correct_count}/{total_questions}",
        "feedback": feedback,
    }), result["status"]



@classroom_bp.route("/assignment/<class_val>/<module>")
def assignment(class_val, module):
    """Assignment home"""

    if ich.check_user_session(session) == False:
        return redirect(url_for("auth_bp.login"))
    
    container=init_cosmos('answer',DATABASE)
    #Query quizes in cosmosdb to get the structure for this assignment
    class_val = escape(class_val)
    module = escape(module)
    user_name = escape(session['user_name'])

    # RBB 11/30 TODO will need to come back and join to questions, make sure to 
    # account for possible questions, not just attempted
    query = """
        SELECT
            c.PartitionKey, 
            c.course, 
            c.module, 
            c.answer, 
            c.team, 
            c.question, 
            c.correct,
            (c.datetime = null) ? c.Timestamp : c.datetime datetime    
        FROM c 
        where c.course = @class_val
        and c.module = @module
        and c.team = @user_name
    """

    parameters = [
        {
            "name" : "@class_val",
            "value" : class_val.lower()
        },
        {
            "name" : "@module",
            "value" : str(module).lower()
        },
        {
            "name" : "@user_name",
            "value" : str(user_name).lower()
        }
    ]
    items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
    )

    if len(items)==0:
        return f"No assignment found for class {class_val} and module {module}"

    df=pd.DataFrame(items)

    # rbb we'll check to see if something is returned at all, and if it is, flag
    # where it has been attempted 
    attempted = True
    if not df.empty:
        df=df[df['PartitionKey']==f"{class_val.lower()}_{module}"]        
    if df.empty:
        attempted = False

    # rbb i think this should just be changed to enumerate? prevent missing indices
    assignment = df.groupby('question').agg({'correct' : ['max','count']})
    df1=pd.DataFrame(assignment).reset_index()
    df1.columns = ["_".join(a) for a in df1.columns.to_flat_index()]
    df1.columns = ['Question Number', 'Correct', 'Attempt Count']
    
    qnum, anum = df1['Question Number'].count(), df1['Correct'].sum()
   # df1.sort_values('question',inplace=True)
    #df1.reset_index(drop=True,inplace=True)

    # rbb 8/18 do we need to close the connection?
    return render_template(
        "assignment.html",
        title='Assignment',
        user=session.get("user"),
        table=df1,
        class_val=class_val,
        module=module,
        qnum=qnum,
        anum=anum
    )

@classroom_bp.route("/exercise_review/<exercise>")
def exercise_review(exercise):
    """Exercise Review shows all the students and their progress on an Exercise"""

    course_name=str(exercise).split('_')[0]   

    if ich.check_user_session(session) == False:
        return redirect(url_for("auth_bp.login"))

    if ich.check_authorized_user(session, course_name) == False:
        return redirect(url_for("auth_bp.login"))
    # Step 2 get the exercise Structure
     
    # Step 2 get the exercise Structure
    container=init_cosmos('answer',DATABASE)
    #Query quizes in cosmosdb to get the structure for this assignment
    # TODO rbb need to update to wrap queries in something where redirects on bad query
    query = """
    SELECT 
        c.PartitionKey, 
        c.course, 
        c.module, 
        c.answer, 
        c.team, 
        c.question, 
        c.correct,
        (c.datetime = null) ? c.Timestamp : c.datetime datetime    
    FROM c 
    where c.PartitionKey = @id
    """

    # rbb 08/13 - update to parameterized queries
    parameters = [
        {
            "name" : "@id",
            "value" : exercise.lower()
        },
    ]

    items = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True )) 
    if len(items)==0:
        return f"No assignment found with the name of {exercise}"
    
    df=pd.DataFrame(items)
    df['question'] = pd.to_numeric(df['question'])

    if not df.empty:
        # Ensure 'datetime' is in the DataFrame and properly formatted
        df['datetime'] = pd.to_datetime(df['datetime'])

        # Add quarter and year columns
        df['quarter'] = df['datetime'].dt.quarter
        df['year'] = df['datetime'].dt.year

        # Filter out rows with NaN in 'quarter' or 'year'
        df = df.dropna(subset=['quarter', 'year'])

        # Generate the table for correctness (1 = right, 0 = wrong) and total score
        df_correct = df.copy().groupby(['team', 'question']).agg({'correct': 'max'}).reset_index()
        table_correct = df_correct.pivot_table(index='team', columns='question', values='correct').reset_index()
        table_correct['score'] = table_correct.iloc[:, 1:].sum(axis=1)  # Calculate total score
        table_correct = table_correct.fillna(0)  # Replace NaN with 0
        table_correct.columns.name = None  # Remove multi-index header

        # Add quarter and year to the correctness table
        table_correct = table_correct.merge(
            df[['team', 'quarter', 'year']].drop_duplicates(),
            on='team',
            how='left'
        )

        # Generate the table for total attempts
        df_attempts = df.copy().groupby(['team', 'question'])['answer'].count().reset_index()
        table_attempts = df_attempts.pivot_table(index='team', columns='question', values='answer').reset_index()
        table_attempts = table_attempts.fillna(0)  # Replace NaN with 0
        table_attempts.columns.name = None  # Remove multi-index header

        # Add quarter and year to the attempts table
        table_attempts = table_attempts.merge(
            df[['team', 'quarter', 'year']].drop_duplicates(),
            on='team',
            how='left'
        )

        return render_template(
            "exercise_review.html",
            title='Exercise Review',
            user=session.get("user"),
            table_correct=table_correct,
            table_attempts=table_attempts,
            exercise=exercise
        )

@classroom_bp.route("/exercise_review_log/<exercise>/<questionnum>")
def exercise_review_open(exercise,questionnum):
    """Exercise Review shows all the students and their progress on an Exercise"""

    course_name=str(exercise).split('_')[0]   

    if not ich.check_user_session(session):
        redirect(url_for("auth_bp.login"))

    if not ich.check_authorized_user(session, course_name):
        redirect(url_for("auth_bp.login"))
    
    # Step 2 get the exercise Structure
    container=init_cosmos('quiz',DATABASE)
    #Query quizes in cosmosdb to get the structure for this assignment
    query = "SELECT * FROM c where c.id='{}'".format(exercise.lower())
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True )) 
    if len(items)==0:
        return "No assignment found with the name of {}".format(exercise)
    assignment=items[0]['questions']
    # Step 3 get all the attempts made for that exercise
    table_service = TableService(account_name=Keys.account_name, account_key=Keys.storage_key)
    tasks = table_service.query_entities('attempts', filter=f"PartitionKey eq '{exercise}'") 
    df=pd.DataFrame(tasks)
    # Step 4 construct dataframe to send to html page
    df2=df[df.question==questionnum]
    return render_template("exercise_review.html",title='Exercise Review',user=session.get("user_name"),tables=[df2.to_html(classes='data',index=False)], exercise=exercise)

@classroom_bp.route("/exercise_form/<exercise>",methods=['GET','POST'])
def exercise_form(exercise):
    """Exercise Form"""
    #Step 1 get user information
    ich.check_user_session(session)

    # Step 2 get the exercise Structure
    container=init_cosmos('quiz',DATABASE)
    #Query quizes in cosmosdb to get the structure for this assignment
    query = "SELECT * FROM c where c.id='{}'".format(exercise.lower())
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True )) 
    if len(items)==0:
        return "No assignment found with the name of {}".format(exercise)
    qnum=len(items[0]['questions'])
    #step 3 create form for that exercise
    class A(FlaskForm):
        a1 = StringField("Question Label")
    
    class B(FlaskForm):
        q=FieldList(FormField(A),min_entries=qnum)
        s=SubmitField("Submit Form")

    form=B()

    return render_template("exercise_form.html",form=form)

@classroom_bp.route("/studentcenter",methods=['GET','POST'])
def student_center():
    items=[]
    if not session.get("user"):
        return redirect(url_for("auth_bp.login"))
    if request.method=='POST':
        #Get course name
        class_name=request.form['wg1']
        #Get quiz format from Cosmos
        container=init_cosmos('quiz',DATABASE)
        query = "SELECT * FROM c where c.class='{}' ORDER BY c.module".format(class_name.lower())
        items = list(container.query_items(
            query=query,
            enable_cross_partition_query=True )) 
        #Get username
        user_name=session['user'].get('preferred_username').split('@')[0]
        #Get all attempts for that person
        table_service = TableService(account_name=Keys.account_name, account_key=Keys.storage_key)
        tasks = table_service.query_entities('attempts', filter=f"team eq '{user_name}'")
        df=pd.DataFrame(tasks)
        #filter for correct answers and course name
        df1=df[(df['correct']==1)&(df['course']==f"{class_name.lower()}")].copy()
        #Loop through all the question in the quiz and update any the user got correct
        for i in range(0,len(items)):
            for j in range(0,len(items[i]['questions'])):
                if len(df1[(df1.question==str(items[i]['questions'][j]['question_num']))&(df1.module==str(items[i]['module']))])>0:
                    items[i]['questions'][j]['correct']=True       
    return render_template("studentcenter.html",title='Student Center',form=ClassForm(),user=session["user"],items=items)

# rbb 8/18 need a route to update questions
@classroom_bp.route("/update_question",methods=['POST'])
def update_question():

    #user_name = ich.check_user_session(session)
    data = json.loads(request.get_json())
    try:
        class_val = data['class_val']
        module_val = data['module_val']
        question_val = data['question']
        updated_by = data['user']
    except:
        return 401

    query = """
        SELECT
            *
        FROM quiz q
        where q.class = @class_val
        and q.module = @module_val
    """

    parameters = [
        {
            "name" : "@class_val",
            "value" : class_val.lower()
        },
        {
            "name" : "@module_val",
            "value" : int(module_val)
        },
    ]

    container=init_cosmos('quiz',DATABASE)

    result = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True))
    


    if len(result) != 1:
        return "Error in results",401
    

    # needs to appropriate handle status codes and check for errors
    #if ich.check_permissions(user_name, 'update_question'):

    for i, question in enumerate(result[0]['questions']):        
        if question['question_num'] == question_val['question_num']:
            # rbb 08/26 do we need to validate the data in the question field?
            result[0]['questions'][i] = question_val
            result[0]['questions'][i]['updated_by'] = updated_by
            result[0]['questions'][i]['update_datetime'] = str(dt.datetime.now())
            break

    container.replace_item(item=result[0]['id'], body=result[0])

    return "success", 200