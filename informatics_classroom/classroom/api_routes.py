"""
REST API routes for classroom functionality (React SPA)
"""
from flask import jsonify, request
from informatics_classroom.classroom import classroom_bp
from informatics_classroom.auth.jwt_utils import require_jwt_token, require_role
from informatics_classroom.auth.class_auth import (
    require_class_role,
    require_class_permission,
    require_quiz_permission,
    get_user_managed_classes,
    assign_class_role,
    remove_class_role,
    update_class_role,
    get_class_members,
    validate_role
)
from informatics_classroom.classroom.routes import (
    get_classes_for_user,
    get_quizzes_for_user,
    get_user_answers_for_quiz,
    get_current_user,
    get_modules_for_class,
    has_class_access,
    set_object,
    get_quiz,
    DATABASE
)
from informatics_classroom.database.factory import get_database_adapter
import pandas as pd


# ========== STUDENT CENTER API ==========

@classroom_bp.route('/api/student/courses', methods=['GET'])
@require_jwt_token
def api_get_student_courses():
    """
    Get all courses accessible to the current student.
    Returns: List of course names
    """
    try:
        user_id = request.jwt_user.get('user_id') or request.jwt_user.get('email', '').split('@')[0]
        courses = get_classes_for_user(user_id)

        return jsonify({
            'success': True,
            'courses': courses
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/student/progress', methods=['GET'])
@require_jwt_token
def api_get_student_progress():
    """
    Get student progress for a specific course.
    Query params: course (required)
    Returns: Module progress with question status
    """
    try:
        course = request.args.get('course')
        if not course:
            return jsonify({
                'success': False,
                'error': 'Course parameter required'
            }), 400

        user_id = request.jwt_user.get('user_id') or request.jwt_user.get('email', '').split('@')[0]
        user_data = get_current_user(user_id)

        if not user_data:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        team = user_data[0].get('team', user_id)

        # Get all quizzes for the course
        db = get_database_adapter()
        quizzes = db.query('quiz', filters={'class': course})

        # Build progress data
        progress_data = []
        for quiz in quizzes:
            module = quiz.get('module')
            questions = quiz.get('questions', [])

            # Get user answers for this module
            answers = get_user_answers_for_quiz(course, module, team)

            # Build question status
            question_status = []
            for question in questions:
                question_num = question.get('question_num')

                # Find if user answered this question correctly
                user_answer = next(
                    (a for a in answers if a.get('question') == str(question_num)),
                    None
                )

                question_status.append({
                    'question_num': question_num,
                    'answered': user_answer is not None,
                    'correct': user_answer.get('correct', False) if user_answer else False
                })

            progress_data.append({
                'module': module,
                'module_name': quiz.get('module_name', f'Module {module}'),
                'questions': question_status,
                'total_questions': len(questions),
                'answered_questions': sum(1 for q in question_status if q['answered']),
                'correct_questions': sum(1 for q in question_status if q['correct'])
            })

        return jsonify({
            'success': True,
            'course': course,
            'progress': progress_data
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/student/dashboard', methods=['GET'])
@require_jwt_token
def api_get_student_dashboard():
    """
    Get complete student dashboard data.
    Returns: User info, accessible courses, and overall progress summary
    """
    try:
        user_id = request.jwt_user.get('user_id') or request.jwt_user.get('email', '').split('@')[0]
        user_data = get_current_user(user_id)

        if not user_data:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        user = user_data[0]
        courses = get_classes_for_user(user_id)

        # Get overall progress summary
        course_summaries = []
        for course in courses:
            db = get_database_adapter()
            quizzes = db.query('quiz', filters={'class': course})

            total_questions = sum(len(q.get('questions', [])) for q in quizzes)

            # Get all answers for this course
            team = user.get('team', user_id)
            total_answered = 0
            total_correct = 0

            for quiz in quizzes:
                module = quiz.get('module')
                answers = get_user_answers_for_quiz(course, module, team)

                # Count unique questions answered
                answered_questions = set(a.get('question') for a in answers)
                total_answered += len(answered_questions)

                # Count correct answers
                total_correct += sum(1 for a in answers if a.get('correct', False))

            course_summaries.append({
                'course': course,
                'total_modules': len(quizzes),
                'total_questions': total_questions,
                'answered_questions': total_answered,
                'correct_questions': total_correct,
                'completion_percentage': round((total_answered / total_questions * 100) if total_questions > 0 else 0, 1)
            })

        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'email': request.jwt_user.get('email'),
                'display_name': request.jwt_user.get('display_name'),
                'team': user.get('team', user_id)
            },
            'courses': courses,
            'course_summaries': course_summaries
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== QUIZ TAKING API ==========

@classroom_bp.route('/api/quiz/details', methods=['GET'])
@require_jwt_token
def api_get_quiz_details():
    """
    Get quiz details for taking.
    Query params: course, module
    Returns: Quiz questions and metadata
    """
    try:
        course = request.args.get('course')
        module = request.args.get('module')

        if not course or not module:
            return jsonify({
                'success': False,
                'error': 'Course and module parameters required'
            }), 400

        db = get_database_adapter()
        quizzes = db.query('quiz', filters={'class': course, 'module': int(module)})

        if not quizzes:
            return jsonify({
                'success': False,
                'error': 'Quiz not found'
            }), 404

        quiz = quizzes[0]

        # Get user's previous answers
        user_id = request.jwt_user.get('user_id') or request.jwt_user.get('email', '').split('@')[0]
        user_data = get_current_user(user_id)
        team = user_data[0].get('team', user_id) if user_data else user_id

        answers = get_user_answers_for_quiz(course, module, team)

        # Build question data with user answers
        questions_with_answers = []
        for question in quiz.get('questions', []):
            question_num = question.get('question_num')
            user_answer = next(
                (a for a in answers if a.get('question') == str(question_num)),
                None
            )

            questions_with_answers.append({
                'question_num': question_num,
                'question_text': question.get('question_text', ''),
                'answers': question.get('answers', []),
                'open': question.get('open', False),
                'user_answer': user_answer.get('answer') if user_answer else None,
                'is_correct': user_answer.get('correct') if user_answer else None
            })

        return jsonify({
            'success': True,
            'quiz': {
                'id': quiz.get('id'),
                'course': course,
                'module': module,
                'module_name': quiz.get('module_name', f'Module {module}'),
                'questions': questions_with_answers
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/quiz/submit-answer', methods=['POST'])
@require_jwt_token
def api_submit_answer():
    """
    Submit a single answer to a quiz question.
    Body: { course, module, question_num, answer }
    Returns: { correct, feedback }
    """
    try:
        data = request.get_json()
        course = data.get('course')
        module = data.get('module')
        question_num = data.get('question_num')
        answer = data.get('answer')

        if not all([course, module, question_num, answer]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400

        user_id = request.jwt_user.get('user_id') or request.jwt_user.get('email', '').split('@')[0]
        user_data = get_current_user(user_id)
        team = user_data[0].get('team', user_id) if user_data else user_id

        # Get quiz and check answer
        db = get_database_adapter()
        query = """
            SELECT (q->>'question_num')::int as question_num,
                   q->>'correct_answer' as correct_answer,
                   (q->>'open')::boolean as open
            FROM quiz, jsonb_array_elements(data->'questions') as q
            WHERE data->>'class' = $1 AND (data->>'module')::int = $2
              AND (q->>'question_num')::int = $3
        """
        parameters = [
            {"name": "$1", "value": course},
            {"name": "$2", "value": int(module)},
            {"name": "$3", "value": int(question_num)}
        ]
        questions = db.query_raw('quiz', query, parameters)

        if not questions:
            return jsonify({
                'success': False,
                'error': 'Question not found'
            }), 404

        question = questions[0]
        is_open = question.get('open', False)
        correct_answer = str(question.get('correct_answer', ''))

        # Check if answer is correct (open questions are always correct)
        is_correct = is_open or (str(answer) == correct_answer)

        # Store answer in database
        import uuid
        import datetime as dt
        answer_record = {
            'PartitionKey': f"{course}_{module}",
            'id': str(uuid.uuid4()),
            'course': course,
            'module': int(module),
            'team': team,
            'question': str(question_num),
            'open': is_open,
            'answer': str(answer),
            'correct': is_correct,
            'datetime': dt.datetime.utcnow().isoformat()
        }

        db.upsert('answer', answer_record)

        return jsonify({
            'success': True,
            'correct': is_correct,
            'feedback': 'Correct!' if is_correct else 'Incorrect. Try again.',
            'is_open': is_open
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== QUIZ BUILDER API (INSTRUCTOR) ==========

@classroom_bp.route('/api/instructor/classes', methods=['GET'])
@require_jwt_token
def api_get_instructor_classes():
    """
    Get all classes the user can manage with detailed metadata.
    Returns: {
        success,
        classes: [{
            id, name, owner, role, quiz_count, student_count,
            created_at, can_delete
        }]
    }
    """
    try:
        user = request.jwt_user
        user_id = user.get('user_id') or user.get('email', '').split('@')[0]
        is_admin = 'admin' in user.get('roles', [])

        db = get_database_adapter()

        # Get all quizzes to extract class information
        all_quizzes = db.query('quiz', filters={})

        # Get unique classes
        if is_admin:
            class_names = list(set(q.get('class') for q in all_quizzes if q.get('class')))
        else:
            class_names = get_user_managed_classes(user, min_role='ta')

        # Build class metadata
        classes_metadata = []
        for class_name in class_names:
            # Count quizzes for this class
            class_quizzes = [q for q in all_quizzes if q.get('class') == class_name]
            quiz_count = len(class_quizzes)

            # Get class owner (first quiz owner)
            owner = None
            created_at = None
            if class_quizzes:
                # Sort by created_at to find the original quiz
                sorted_quizzes = sorted(
                    [q for q in class_quizzes if q.get('created_at')],
                    key=lambda x: x.get('created_at', '')
                )
                if sorted_quizzes:
                    owner = sorted_quizzes[0].get('owner')
                    created_at = sorted_quizzes[0].get('created_at')

            # Get user's role for this class
            role = get_user_class_role(user, class_name) if not is_admin else 'admin'

            # Count students from class_memberships (actual assigned members)
            from informatics_classroom.auth.class_auth import get_class_members
            members = get_class_members(class_name)
            student_count = len(members)

            # Determine if user can delete this class
            can_delete = is_admin or (owner and owner == user_id) or role == 'instructor'

            classes_metadata.append({
                'id': class_name,
                'name': class_name,
                'owner': owner,
                'role': role,
                'quiz_count': quiz_count,
                'student_count': student_count,
                'created_at': created_at,
                'can_delete': can_delete
            })

        # Sort by name
        classes_metadata.sort(key=lambda x: x['name'])

        return jsonify({
            'success': True,
            'classes': classes_metadata
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/classes', methods=['POST'])
@require_jwt_token
@require_role(['admin', 'instructor'])
def api_create_class():
    """
    Create a new class.
    Only instructors and admins can create classes.
    Returns: { success, class }
    """
    try:
        data = request.get_json()
        class_name = data.get('name', '').strip()

        if not class_name:
            return jsonify({
                'success': False,
                'error': 'Class name is required'
            }), 400

        user = request.jwt_user
        user_id = user.get('user_id') or user.get('email', '').split('@')[0]

        db = get_database_adapter()

        # Check if class already exists
        all_quizzes = db.query('quiz', filters={})
        existing_classes = set(q.get('class') for q in all_quizzes if q.get('class'))

        if class_name in existing_classes:
            return jsonify({
                'success': False,
                'error': f'Class "{class_name}" already exists'
            }), 400

        # Create initial membership record for the creator as instructor
        # This is done by adding class to user's class_memberships
        assign_class_role(user_id, class_name, 'instructor', assigned_by=user_id)

        return jsonify({
            'success': True,
            'class': {
                'id': class_name,
                'name': class_name,
                'owner': user_id,
                'role': 'instructor',
                'quiz_count': 0,
                'student_count': 0,
                'can_delete': True
            }
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/classes/<class_id>', methods=['DELETE'])
@require_jwt_token
def api_delete_class(class_id):
    """
    Delete a class and all its associated data (quizzes, answers, memberships).
    Only class owners, instructors, and admins can delete.
    Returns: { success }
    """
    try:
        user = request.jwt_user
        user_id = user.get('user_id') or user.get('email', '').split('@')[0]
        is_admin = 'admin' in user.get('roles', [])

        db = get_database_adapter()

        # Get all quizzes for this class to determine owner
        all_quizzes = db.query('quiz', filters={})
        class_quizzes = [q for q in all_quizzes if q.get('class') == class_id]

        if not class_quizzes:
            return jsonify({
                'success': False,
                'error': 'Class not found or has no quizzes'
            }), 404

        # Check permissions
        user_role = get_user_class_role(user, class_id)
        class_owner = None
        if class_quizzes:
            sorted_quizzes = sorted(
                [q for q in class_quizzes if q.get('created_at')],
                key=lambda x: x.get('created_at', '')
            )
            if sorted_quizzes:
                class_owner = sorted_quizzes[0].get('owner')

        can_delete = is_admin or (class_owner and class_owner == user_id) or user_role == 'instructor'

        if not can_delete:
            return jsonify({
                'success': False,
                'error': 'You do not have permission to delete this class'
            }), 403

        # Delete all quizzes for this class
        for quiz in class_quizzes:
            quiz_id = quiz.get('id')
            if quiz_id:
                db.delete('quiz', quiz_id)

        # Note: We don't delete answer records to preserve historical data
        # But we could add a flag or separate them if needed

        # Remove class membership records
        # This would require direct database access to the user records
        # For now, we'll rely on the quiz deletion to effectively remove the class

        return jsonify({
            'success': True
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/quizzes/create', methods=['POST'])
@require_jwt_token
@require_class_role(['instructor', 'ta'], class_from='body.class')
def api_create_quiz():
    """
    Create a new quiz with questions.
    Requires instructor or TA role for the specified class.
    Body: { class, module, title, description, questions: [...] }
    Returns: { success, quiz_id }
    """
    try:
        data = request.get_json()
        class_val = data.get('class')
        module = data.get('module')
        title = data.get('title')
        description = data.get('description', '')
        questions = data.get('questions', [])

        if not all([class_val, module, title, questions]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: class, module, title, questions'
            }), 400

        user_id = request.jwt_user.get('user_id') or request.jwt_user.get('email', '').split('@')[0]

        # Build quiz document
        import uuid
        import datetime as dt
        quiz_id = f"{class_val}_{module}"

        quiz = {
            'id': quiz_id,
            'class': class_val,
            'module': int(module),
            'title': title,
            'module_name': title,
            'description': description,
            'questions': questions,
            'owner': user_id,
            'created_at': dt.datetime.utcnow().isoformat(),
            'updated_at': dt.datetime.utcnow().isoformat()
        }

        # Store in database
        db = get_database_adapter()
        db.upsert('quiz', quiz)

        return jsonify({
            'success': True,
            'quiz_id': quiz_id
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/quizzes/<quiz_id>/edit', methods=['GET'])
@require_jwt_token
@require_quiz_permission('manage_quizzes')
def api_get_quiz_for_edit(quiz_id):
    """
    Get quiz for editing.
    Requires manage_quizzes permission for the quiz's class.
    Returns: { success, quiz: {...} }
    """
    try:
        # Get quiz from database (permission already validated by decorator)
        db = get_database_adapter()
        quiz = db.get('quiz', quiz_id)

        if not quiz:
            return jsonify({
                'success': False,
                'error': 'Quiz not found'
            }), 404

        return jsonify({
            'success': True,
            'quiz': quiz
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/quizzes/<quiz_id>/update', methods=['PUT'])
@require_jwt_token
@require_quiz_permission('manage_quizzes')
def api_update_quiz(quiz_id):
    """
    Update existing quiz.
    Requires manage_quizzes permission for the quiz's class.
    Body: { title, description, questions: [...] }
    Returns: { success }
    """
    try:
        data = request.get_json()

        # Get existing quiz (permission already validated by decorator)
        db = get_database_adapter()
        quiz = db.get('quiz', quiz_id)

        if not quiz:
            return jsonify({
                'success': False,
                'error': 'Quiz not found'
            }), 404

        # Update fields
        import datetime as dt
        user = request.jwt_user
        user_id = user.get('user_id') or user.get('email') or user.get('id')
        now = dt.datetime.utcnow().isoformat()

        quiz['title'] = data.get('title', quiz['title'])
        quiz['module_name'] = data.get('title', quiz['module_name'])
        quiz['description'] = data.get('description', quiz['description'])

        # Track question modifications
        old_questions = quiz.get('questions', [])
        new_questions = data.get('questions', quiz['questions'])

        # Update questions with change tracking
        for new_q in new_questions:
            q_num = new_q.get('question_num')
            if q_num is None:
                continue

            # Find old version of this question
            old_q = next((q for q in old_questions if q.get('question_num') == q_num), None)

            # Initialize change_log if it doesn't exist
            if 'change_log' not in new_q:
                new_q['change_log'] = []

            # Check if question was modified
            if old_q:
                old_answer = old_q.get('correct_answer')
                new_answer = new_q.get('correct_answer')
                old_open = old_q.get('open', False)
                new_open = new_q.get('open', False)

                # If anything changed, log it
                if old_answer != new_answer or old_open != new_open:
                    change_entry = {
                        'question_num': q_num,
                        'change_type': 'update',
                        'updated_by': user_id,
                        'update_datetime': now,
                        'old_value': {
                            'correct_answer': old_answer,
                            'open': old_open
                        },
                        'new_value': {
                            'correct_answer': new_answer,
                            'open': new_open
                        }
                    }
                    new_q['change_log'].append(change_entry)
                else:
                    # No change, preserve old change_log
                    new_q['change_log'] = old_q.get('change_log', [])
            else:
                # New question, log creation
                change_entry = {
                    'question_num': q_num,
                    'change_type': 'create',
                    'updated_by': user_id,
                    'update_datetime': now,
                    'old_value': None,
                    'new_value': {
                        'correct_answer': new_q.get('correct_answer'),
                        'open': new_q.get('open', False)
                    }
                }
                new_q['change_log'].append(change_entry)

        quiz['questions'] = new_questions
        quiz['updated_at'] = now
        quiz['updated_by'] = user_id

        # Save to database
        db.upsert('quiz', quiz)

        return jsonify({
            'success': True
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/instructor/quizzes', methods=['GET'])
@require_jwt_token
@require_role(['admin', 'instructor', 'ta'])
def api_get_instructor_quizzes():
    """
    Get all quizzes for classes where user has instructor/TA role.
    Optional query param: class - filter quizzes by specific class
    Returns: { success, quizzes: [{id, class, module, title, description, question_count, created_at, updated_at}] }
    """
    try:
        user = request.jwt_user
        user_roles = user.get('roles', [])

        # Get optional class filter from query params
        class_filter = request.args.get('class')

        db = get_database_adapter()

        # Admins can see all quizzes
        if 'admin' in user_roles:
            quizzes = db.query('quiz', filters={})
        else:
            # Get classes where user has at least TA role
            managed_classes = get_user_managed_classes(user, min_role='ta')

            if not managed_classes:
                # User has no managed classes, return empty list
                quizzes = []
            else:
                # Get all quizzes for managed classes
                all_quizzes = db.query('quiz', filters={})
                quizzes = [q for q in all_quizzes if q.get('class') in managed_classes]

        # Apply class filter if provided
        if class_filter:
            quizzes = [q for q in quizzes if q.get('class') == class_filter]

        # Format quiz list with summary information
        quiz_list = []
        for quiz in quizzes:
            quiz_list.append({
                'id': quiz.get('id'),
                'class': quiz.get('class'),
                'module': quiz.get('module'),
                'title': quiz.get('title'),
                'description': quiz.get('description', ''),
                'question_count': len(quiz.get('questions', [])),
                'owner': quiz.get('owner'),
                'created_at': quiz.get('created_at'),
                'updated_at': quiz.get('updated_at')
            })

        # Sort by class, then module (handle None values)
        quiz_list.sort(key=lambda q: (q['class'] or '', q['module'] or 0))

        return jsonify({
            'success': True,
            'quizzes': quiz_list
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/quizzes/<quiz_id>', methods=['DELETE'])
@require_jwt_token
@require_quiz_permission('manage_quizzes')
def api_delete_quiz(quiz_id):
    """
    Delete a quiz.
    Requires manage_quizzes permission for the quiz's class.
    Note: TAs can create/edit quizzes but typically only instructors should delete.
          The permission check allows both, but frontend can restrict UI access.
    Returns: { success }
    """
    try:
        # Get quiz (permission already validated by decorator)
        db = get_database_adapter()
        quiz = db.get('quiz', quiz_id)

        if not quiz:
            return jsonify({
                'success': False,
                'error': 'Quiz not found'
            }), 404

        # Delete the quiz
        db.delete('quiz', quiz_id)

        return jsonify({
            'success': True
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/classes/<class_id>/grades', methods=['GET'])
@require_jwt_token
@require_class_permission('view_analytics', class_from='path.class_id')
def api_get_class_grades(class_id):
    """
    Get grade matrix for all students and quizzes in a class.
    Returns pivot table data with students as rows and quizzes as columns.
    Requires view_analytics permission (instructor, TA, or grader).
    Returns: {
        success,
        students: [student_ids],
        quizzes: [{id, module, title, question_count}],
        grades: {student_id: {quiz_id: {score, total, percentage, submitted}}}
    }
    """
    try:
        db = get_database_adapter()

        # Get all quizzes for this class
        all_quizzes = db.query('quiz', filters={})
        class_quizzes = [q for q in all_quizzes if q.get('class') == class_id]

        if not class_quizzes:
            return jsonify({
                'success': True,
                'students': [],
                'quizzes': [],
                'grades': {}
            })

        # Build quiz metadata
        quiz_metadata = []
        for quiz in class_quizzes:
            quiz_metadata.append({
                'id': quiz.get('id'),
                'module': quiz.get('module'),
                'title': quiz.get('title'),
                'question_count': len(quiz.get('questions', []))
            })

        # Sort quizzes by module
        quiz_metadata.sort(key=lambda q: (q['module'] or 0))

        # Get all answers for quizzes in this class
        query = """
            SELECT
                data->>'team' as team,
                data->>'question' as question,
                (data->>'correct')::boolean as correct,
                (data->>'module')::int as module,
                LOWER(data->>'course') as course
            FROM answer
            WHERE LOWER(data->>'course') = LOWER($1)
              AND data->>'datetime' IS NOT NULL
        """
        params = [{'name': '$1', 'value': class_id}]
        answers = db.query_raw('answer', query, params)

        if not answers:
            return jsonify({
                'success': True,
                'students': [],
                'quizzes': quiz_metadata,
                'grades': {}
            })

        # Build grades matrix
        # Structure: {student_id: {quiz_id: {score, total, percentage, submitted}}}
        df = pd.DataFrame(answers)
        df['team'] = df['team'].fillna('Unknown').astype(str)

        students = sorted(df['team'].unique())
        grades_matrix = {}

        for student in students:
            student_df = df[df['team'] == student]
            grades_matrix[student] = {}

            for quiz in class_quizzes:
                quiz_id = quiz.get('id')
                quiz_module = quiz.get('module')
                quiz_questions = quiz.get('questions', [])
                total_questions = len(quiz_questions)

                if total_questions == 0:
                    continue

                # Get active question numbers for this quiz
                active_questions = {str(q['question_num']) for q in quiz_questions}

                # Filter student answers for this quiz (by module)
                quiz_answers = student_df[student_df['module'] == quiz_module]
                quiz_answers = quiz_answers[quiz_answers['question'].isin(active_questions)]

                if quiz_answers.empty:
                    # Student hasn't submitted this quiz
                    grades_matrix[student][quiz_id] = {
                        'score': 0,
                        'total': total_questions,
                        'percentage': 0,
                        'submitted': False
                    }
                else:
                    # Calculate score (count correct answers)
                    # Group by question and check if any attempt was correct
                    correct_questions = set()
                    for question in active_questions:
                        q_answers = quiz_answers[quiz_answers['question'] == question]
                        if not q_answers.empty and q_answers['correct'].any():
                            correct_questions.add(question)

                    score = len(correct_questions)
                    percentage = round((score / total_questions * 100), 1) if total_questions > 0 else 0

                    grades_matrix[student][quiz_id] = {
                        'score': score,
                        'total': total_questions,
                        'percentage': percentage,
                        'submitted': True
                    }

        return jsonify({
            'success': True,
            'students': students,
            'quizzes': quiz_metadata,
            'grades': grades_matrix
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== TOKEN GENERATOR API (INSTRUCTOR) ==========

@classroom_bp.route('/api/instructor/class-modules', methods=['GET'])
@require_jwt_token
def api_get_class_modules():
    """
    Get all classes and their modules for the user.
    Returns classes based on user's class memberships (already filtered by access).
    Returns: { classes: [string], class_modules: {class: [modules]} }
    """
    try:
        user_id = request.jwt_user.get('user_id') or request.jwt_user.get('email', '').split('@')[0]
        accessible_classes = get_classes_for_user(user_id)

        class_modules = {}
        for class_val in accessible_classes:
            modules = get_modules_for_class(class_val)
            class_modules[class_val] = modules

        return jsonify({
            'success': True,
            'classes': accessible_classes,
            'class_modules': class_modules
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/tokens/generate', methods=['POST'])
@require_jwt_token
@require_class_role(['instructor', 'ta', 'student'], class_from='body.class_val')
def api_generate_token():
    """
    Generate a personal access token for quiz access to a specific class and module.

    Personal tokens are tied to the user's account and provide convenient quiz access
    without requiring repeated authentication. Each token contains the user's ID,
    class, module, and expiration timestamp (24 hours).

    Security Note: Tokens authenticate as the user who generated them and should not
    be shared with others.

    Body: { class_val, module_val }
    Returns: { success, token, expiry }
    """
    try:
        data = request.get_json()
        class_val = data.get('class_val')
        module_val = data.get('module_val')

        if not class_val or not module_val:
            return jsonify({
                'success': False,
                'error': 'Both class_val and module_val are required'
            }), 400

        user_id = request.jwt_user.get('user_id') or request.jwt_user.get('email', '').split('@')[0]

        # Check access
        if not has_class_access(user_id, class_val):
            return jsonify({
                'success': False,
                'error': 'You do not have access to this class'
            }), 403

        # Generate token
        import uuid
        import datetime as dt
        token = str(uuid.uuid4())
        expiry_time = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24)

        token_entry = {
            'id': token,
            'user': user_id,
            'class_val': class_val,
            'module_val': module_val,
            'expiry': expiry_time.isoformat()
        }

        # Store in database
        set_object(token_entry, 'tokens')

        return jsonify({
            'success': True,
            'token': token,
            'expiry': expiry_time.isoformat()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== ASSIGNMENT ANALYSIS API (INSTRUCTOR) ==========

@classroom_bp.route('/api/assignments/analyze', methods=['POST'])
@require_jwt_token
@require_class_permission('view_analytics', class_from='body.class_name')
def api_analyze_assignment():
    """
    Analyze assignment performance for a class/module with optional year filter.
    Requires view_analytics permission for the class (instructor, TA, or grader).
    """
    try:
        data = request.get_json()
        class_name = data.get('class_name', '').strip().lower()
        module_number = data.get('module_number', '').strip()
        year_filter = data.get('year_filter', '').strip()

        if not class_name or not module_number:
            return jsonify({'success': False, 'error': 'Both class_name and module_number are required'}), 400

        # Get quiz to identify active questions
        quiz = get_quiz(class_val=class_name, module_val=module_number)
        if not quiz:
            return jsonify({'success': False, 'error': f'No quiz found for class {class_name} and module {module_number}'}), 404

        active_questions = {str(q['question_num']) for q in quiz[0].get('questions', [])}

        # Query answers from database
        db = get_database_adapter()
        query = """
            SELECT
                data->>'team' as team,
                data->>'question' as question,
                data->>'answer' as answer,
                (data->>'correct')::boolean as correct,
                (data->>'module')::int as module,
                data->>'datetime' as datetime
            FROM answer
            WHERE LOWER(data->>'course') = LOWER($1)
              AND (data->>'module')::int = $2
              AND data->>'datetime' IS NOT NULL
            ORDER BY data->>'datetime' DESC
        """
        params = [
            {'name': '$1', 'value': class_name},
            {'name': '$2', 'value': int(module_number)}
        ]
        items = db.query_raw('answer', query, params)

        if not items:
            return jsonify({'success': False, 'error': 'No answer data found'}), 404

        import pandas as pd
        df = pd.DataFrame(items)

        # Parse datetime
        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce', utc=True)
        df['datetime'] = df['datetime'].dt.tz_convert(None)
        df['question'] = df['question'].astype(str)
        df = df.dropna(subset=['datetime'])

        # Apply year filter if provided
        if year_filter:
            try:
                year_val = int(year_filter)
                df = df[df['datetime'].dt.year == year_val]
            except ValueError:
                pass

        if df.empty:
            return jsonify({'success': False, 'error': 'No data found for specified filters'}), 404

        # Filter to active questions only
        df = df[df['question'].isin(active_questions)]
        df['team'] = df['team'].fillna('UnknownTeam').astype(str)
        df['question'] = df['question'].fillna('UnknownQuestion').astype(str)

        # Build module summary (question-by-question breakdown)
        module_summary = []
        for question_num in sorted(active_questions, key=lambda x: int(x) if x.isdigit() else 999):
            q_df = df[df['question'] == question_num]
            if q_df.empty:
                continue

            total_students = q_df['team'].nunique()
            correct_students = q_df[q_df['correct'] == True]['team'].nunique()
            attempt_count = len(q_df)
            avg_attempts = attempt_count / total_students if total_students > 0 else 0
            percent_correct = (correct_students / total_students * 100) if total_students > 0 else 0

            # Student breakdown
            student_breakdown = []
            student_details = {}
            for team in q_df['team'].unique():
                team_df = q_df[q_df['team'] == team].sort_values('datetime')
                attempts = len(team_df)
                is_correct = team_df['correct'].any()

                student_breakdown.append({
                    'team': team,
                    'attempts': attempts,
                    'correct': bool(is_correct)
                })

                student_details[team] = [
                    {
                        'answer': row['answer'],
                        'correct': bool(row['correct']),
                        'datetime': row['datetime'].isoformat() if pd.notna(row['datetime']) else ''
                    }
                    for _, row in team_df.iterrows()
                ]

            module_summary.append({
                'question': question_num,
                'total_students': total_students,
                'correct_students': correct_students,
                'attempt_count': attempt_count,
                'avg_attempts': round(avg_attempts, 2),
                'percent_correct': round(percent_correct, 2),
                'student_breakdown': student_breakdown,
                'details': student_details
            })

        # Build pivot tables for correctness & attempts
        pivot_correctness_rows = []
        pivot_attempts_rows = []

        for team in sorted(df['team'].unique()):
            team_df = df[df['team'] == team]
            correctness_row = [team]
            attempts_row = [team]

            for question_num in sorted(active_questions, key=lambda x: int(x) if x.isdigit() else 999):
                q_team_df = team_df[team_df['question'] == question_num]
                if q_team_df.empty:
                    correctness_row.append('N/A')
                    attempts_row.append(0)
                else:
                    is_correct = q_team_df['correct'].any()
                    correctness_row.append('✓' if is_correct else '✗')
                    attempts_row.append(len(q_team_df))

            pivot_correctness_rows.append(correctness_row)
            pivot_attempts_rows.append(attempts_row)

        question_cols = ['Student'] + [f'Q{q}' for q in sorted(active_questions, key=lambda x: int(x) if x.isdigit() else 999)]

        return jsonify({
            'success': True,
            'module_summary': module_summary,
            'table_correctness': {
                'columns': question_cols,
                'rows': pivot_correctness_rows
            },
            'table_attempts': {
                'columns': question_cols,
                'rows': pivot_attempts_rows
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== EXERCISE REVIEW API (STUDENT) ==========

@classroom_bp.route('/api/student/exercise-review', methods=['GET'])
@require_jwt_token
def api_exercise_review():
    """Get student's progress across all accessible classes/modules."""
    try:
        user_id = request.jwt_user.get('user_id') or request.jwt_user.get('email', '').split('@')[0]

        # Get accessible quizzes
        quizzes = get_quizzes_for_user(user_id, include_answers=1)

        if not quizzes:
            return jsonify({'success': True, 'classes': []}), 200

        db = get_database_adapter()
        progress_data = {}

        for quiz in quizzes:
            class_name = quiz.get('class')
            module = quiz.get('module', 'Unknown')
            questions = quiz.get('questions', [])
            partition_key = f"{class_name}_{module}"

            active_questions = {str(q['question_num']) for q in questions}

            # Fetch answers for this quiz
            answer_query = """
                SELECT data->>'question' as question,
                       (data->>'correct')::boolean as correct
                FROM answer
                WHERE data->>'PartitionKey' = $1 AND data->>'team' = $2
            """
            answer_parameters = [
                {'name': '$1', 'value': partition_key},
                {'name': '$2', 'value': user_id}
            ]
            answers = db.query_raw('answer', answer_query, answer_parameters)

            # Filter to active questions
            filtered_answers = [a for a in answers if str(a['question']) in active_questions]
            questions_attempted = {a['question'] for a in filtered_answers}
            correct_questions = {a['question'] for a in filtered_answers if a.get('correct', 0) == 1}

            total_questions = len(active_questions)
            num_attempted = len(questions_attempted)
            num_correct = len(correct_questions)

            if class_name not in progress_data:
                progress_data[class_name] = {
                    'class': class_name,
                    'overall_progress': 0,
                    'overall_correctness': 0,
                    'modules': {},
                    'total_questions': 0,
                    'questions_attempted': 0,
                    'questions_correct': 0
                }

            if module not in progress_data[class_name]['modules']:
                progress_data[class_name]['modules'][module] = {
                    'module': module,
                    'total_questions': 0,
                    'questions_attempted': 0,
                    'questions_correct': 0
                }

            progress_data[class_name]['modules'][module]['total_questions'] += total_questions
            progress_data[class_name]['modules'][module]['questions_attempted'] += num_attempted
            progress_data[class_name]['modules'][module]['questions_correct'] += num_correct

            progress_data[class_name]['total_questions'] += total_questions
            progress_data[class_name]['questions_attempted'] += num_attempted
            progress_data[class_name]['questions_correct'] += num_correct

        # Calculate percentages
        for class_data in progress_data.values():
            total_questions = class_data['total_questions']
            total_attempted = class_data['questions_attempted']
            total_correct = class_data['questions_correct']

            class_data['overall_progress'] = round((total_attempted / total_questions) * 100, 2) if total_questions else 0
            class_data['overall_correctness'] = round((total_correct / total_attempted) * 100, 2) if total_attempted else 0

            # Convert modules dict to list
            for module_data in class_data['modules'].values():
                module_data['module_progress'] = round((module_data['questions_attempted'] / module_data['total_questions']) * 100, 2) if module_data['total_questions'] else 0
                module_data['module_correctness'] = round((module_data['questions_correct'] / module_data['questions_attempted']) * 100, 2) if module_data['questions_attempted'] else 0

            class_data['modules'] = list(class_data['modules'].values())

        return jsonify({'success': True, 'classes': list(progress_data.values())}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# CLASS MEMBER MANAGEMENT ENDPOINTS
# ============================================================================

@classroom_bp.route('/api/classes/<class_id>/members', methods=['GET'])
@require_jwt_token
def api_list_class_members(class_id):
    """
    Get all members of a class with their roles.

    Requires manage_members permission for the class.

    Args:
        class_id: Class identifier from URL path

    Returns:
        JSON with list of class members and their roles
    """
    try:
        # Manual permission check since class_id is in URL path
        user = request.jwt_user

        # Check if user has manage_members permission for this class
        from informatics_classroom.auth.class_auth import user_has_class_permission
        if not user_has_class_permission(user, class_id, 'manage_members'):
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions to manage members for this class'
            }), 403

        members = get_class_members(class_id)

        return jsonify({
            'success': True,
            'class_id': class_id,
            'members': members,
            'count': len(members)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/classes/<class_id>/members', methods=['POST'])
@require_jwt_token
def api_add_class_member(class_id):
    """
    Add a user to a class with a specific role.

    Requires manage_members permission for the class.

    Request body:
        user_id: ID of user to add
        role: Role to assign (instructor, ta, student)

    Returns:
        JSON with success status and updated membership
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        user_id = data.get('user_id')
        role = data.get('role')

        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400

        if not role:
            return jsonify({
                'success': False,
                'error': 'role is required'
            }), 400

        # Validate role
        if not validate_role(role):
            return jsonify({
                'success': False,
                'error': f'Invalid role: {role}. Must be one of: instructor, ta, student'
            }), 400

        # Manual permission check since class_id is in URL path
        current_user = request.jwt_user
        from informatics_classroom.auth.class_auth import user_has_class_permission
        if not user_has_class_permission(current_user, class_id, 'manage_members'):
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions to manage members for this class'
            }), 403

        # Get current user for audit trail
        assigned_by = current_user.get('user_id') or current_user.get('email')

        # Assign the role
        result = assign_class_role(user_id, class_id, role, assigned_by=assigned_by)

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': f'User {user_id} added to class {class_id} as {role}',
                'user_id': user_id,
                'class_id': class_id,
                'role': role
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to assign role')
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/classes/<class_id>/members/<user_id>', methods=['PUT'])
@require_jwt_token
def api_update_class_member(class_id, user_id):
    """
    Update a user's role in a class.

    Requires manage_members permission for the class.

    Request body:
        role: New role to assign (instructor, ta, student)

    Returns:
        JSON with success status and updated membership
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        new_role = data.get('role')

        if not new_role:
            return jsonify({
                'success': False,
                'error': 'role is required'
            }), 400

        # Validate role
        if not validate_role(new_role):
            return jsonify({
                'success': False,
                'error': f'Invalid role: {new_role}. Must be one of: instructor, ta, student'
            }), 400

        # Manual permission check since class_id is in URL path
        current_user = request.jwt_user
        from informatics_classroom.auth.class_auth import user_has_class_permission
        if not user_has_class_permission(current_user, class_id, 'manage_members'):
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions to manage members for this class'
            }), 403

        # Get current user for audit trail
        updated_by = current_user.get('user_id') or current_user.get('email')

        # Update the role
        result = update_class_role(user_id, class_id, new_role, updated_by=updated_by)

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': f'User {user_id} role updated to {new_role} in class {class_id}',
                'user_id': user_id,
                'class_id': class_id,
                'role': new_role
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to update role')
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@classroom_bp.route('/api/classes/<class_id>/members/<user_id>', methods=['DELETE'])
@require_jwt_token
def api_remove_class_member(class_id, user_id):
    """
    Remove a user from a class.

    Requires manage_members permission for the class.

    Args:
        class_id: Class identifier from URL path
        user_id: User identifier from URL path

    Returns:
        JSON with success status
    """
    try:
        # Manual permission check since class_id is in URL path
        current_user = request.jwt_user
        from informatics_classroom.auth.class_auth import user_has_class_permission
        if not user_has_class_permission(current_user, class_id, 'manage_members'):
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions to manage members for this class'
            }), 403

        result = remove_class_role(user_id, class_id)

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': f'User {user_id} removed from class {class_id}',
                'user_id': user_id,
                'class_id': class_id
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to remove user from class')
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
