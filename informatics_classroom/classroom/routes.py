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
from markupsafe import escape
import json
import uuid


# rbb setting for testing without authentication
TESTING_MODE = Config.TESTING
DATABASE = 'bids-class'

ClassGroups=sorted(['PMAP','CDA','FHIR','OHDSI'])

#answerkey=load_answerkey('quiz',Config.DATABASE)

# rbb good
@classroom_bp.route('/home')
def landingpage():
    return render_template('home.html',title='Home')

# rbb needs to default to something
@classroom_bp.route("/quiz",methods=['GET','POST'])
def quiz():
    return render_template('quiz.html')

# rbb shouldn't this just be post? needs to check user
@classroom_bp.route("/submit-answer",methods=['GET','POST'])
def submit_answer():

    #user_name = ich.check_user_session(session)

    # rbb 8/18 i think this needs to be a different route, this should always be post
    if request.method=='GET':
        form=AnswerForm()
        return render_template('answerform.html',title='AnswerForm',form=form)
    
    sub_fields=['module', 'team', 'question_num', 'answer_num']
    for field in sub_fields:
        if field not in request.form.keys():
            return jsonify({"message":f"Bad request, missing field {field}"}),400
    # Get the answer key
    if 'class' in request.form.keys():
        #removing use of class as a variable name
        partition_key=request.form['class']
    else:
        partition_key=request.form['class_name']
    module_num=request.form['module']
    module_name=partition_key+"_"+ module_num
    
    

    #container=init_cosmos('quiz',DATABASE)
    #output=container.read_item(item=item_name,partition_key=partition_key)
    #questions=output['questions']
  
    question_num=int(request.form['question_num'])
    answer_num=request.form['answer_num']

    # rbb 09/03

    container=init_cosmos('quiz','bids-class')

    query = """
        SELECT
        c.question_num,
        c.correct_answer,
        c.open
        FROM quiz q
        join c in q.questions
        where q.class = @class_val
        and q.module = @module_val
        and c.question_num = @q_num
    """

    parameters = [
        {
            "name" : "@class_val",
            "value" : partition_key.lower()
        },
        {
            "name" : "@module_val",
            "value" : int(module_num)
        },
        {
            "name" : "@q_num",
            "value" : int(question_num)
        },
    ]

    question = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
    )

    if len(question) != 1:
        return jsonify({"Something went wrong"}),400
    else:
        question = question[0]
    
    # need to quit here if answer key doesn't exist

    attempt = {
        'PartitionKey':module_name,
        'id': str(uuid.uuid4()),
        'course':partition_key,
        'module': module_num,
        # rbb 8/18 should this be user name?
        'team': request.form['team'],
        'question': question_num,
        'answer':str(answer_num)
    }

    #Checks to see if its an open question, if it is empty answer_num so it will return tru
    #Note the attempt dictionary already logged the actual answer  

    #if len(questions[question_num])==0:
    #    answer_num=""  

    # check if open ended question first

    container=init_cosmos('answer','bids-class')

    if ('open' in question.keys()) and (question['open'] == 'True') and answer_num:
        #Log success for team
        nextquestion=''
        attempt['correct']=1
        container.upsert_item(attempt)
        return jsonify({"Message":"Great job! You got it right.","Next Question":nextquestion}),200
    
    elif (str(question['correct_answer'])==str(answer_num)):       
        #Log success for team
        nextquestion=''
        attempt['correct']=1
        container.upsert_item(attempt)
        return jsonify({"Message":"Great job! You got it right.","Next Question":nextquestion}),200
    
    else:
        #Log failure for team
        attempt['correct']=0
        container.upsert_item(attempt)
        return jsonify({"message":"Sorry, wrong answer"}),406  



@classroom_bp.route("/assignment/<class_val>/<module>")
def assignment(class_val, module):
    """Assignment home"""
    # for testing 
    user_name = ich.check_user_session(session)

    container=init_cosmos('quiz',DATABASE)
    #Query quizes in cosmosdb to get the structure for this assignment

    #ignore this for now, will use later
    class_val = escape(class_val)
    module = escape(module)

    query = """
        SELECT
        *
        FROM c 
        where c.class = @class_val
        and c.module = @module
    """

    parameters = [
        {
            "name" : "@class_val",
            "value" : class_val.lower()
        },
        {
            "name" : "@module",
            "value" : int(module)
        },
    ]
 
    items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
    )
    if len(items)==0:
        return f"No assignment found for class {class_val} and module {module}"
    #{}".format(exercise)
    
    assignment=items[0]['questions']

    #Query Tableservice to get all attempts to answer questions for this assignment
    table_service = TableService(account_name=Keys.account_name, account_key=Keys.storage_key)
    tasks = table_service.query_entities('attempts', filter=f"team eq '{user_name}'") 
    df=pd.DataFrame(tasks)
    print(df)
    # rbb we'll check to see if something is returned at all, and if it is, flag
    # where it has been attempted 
    attempted = True
    if not df.empty:
        df=df[df['PartitionKey']==f"{class_val.lower()}_{module}"]        
    if df.empty:
        attempted = False

    print(df)
    print(assignment)
    qnum,anum=0,0
    # rbb i think this should just be changed to enumerate? prevent missing indices
    for i in range(0,len(assignment)):
        q_num=assignment[i]['question_num']
        df['question'] = pd.to_numeric(df.question)
        attempts=len(df[df.question==int(q_num)]) if attempted else 0
        correct=len(df[(df.question==int(q_num))&(df.correct)]) if attempted else 0
        assignment[i]['attempts']=attempts
        assignment[i]['correct']=correct
        qnum+=1
        if correct==True:
            anum+=1
    df1=pd.DataFrame(assignment)
    df1.drop('correct_answer',axis=1, inplace=True)
    df1.sort_values('question_num',inplace=True)
    df1.reset_index(drop=True,inplace=True)

    # rbb 8/18 do we need to close the connection?
    return render_template("assignment.html",title='Assignment',user=session["user"],tables=[df1.to_html(classes='data',index=False)], class_val = class_val, module = module,qnum=qnum,anum=anum)

@classroom_bp.route("/exercise_review/<exercise>")
def exercise_review(exercise):
    """Exercise Review shows all the students and their progress on an Exercise"""
    user_name = ich.check_user_session(session)

    course_name=str(exercise).split('_')[0]   

    if not ich.check_authorized_user(session, course_name):
        return redirect(url_for("auth_bp.login"))
     
    # Step 2 get the exercise Structure
    container=init_cosmos('answer',DATABASE)
    #Query quizes in cosmosdb to get the structure for this assignment
    # TODO rbb need to update to wrap queries in something where redirects on bad query
    query = "SELECT c.PartitionKey, c.course, c.module, c.answer, c.team, c.question, c.correct FROM c where c.PartitionKey = @id"

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
    
    # Step 3 get all the attempts made for that exercise
    #table_service = TableService(account_name=Keys.account_name, account_key=Keys.storage_key)
    #tasks = table_service.query_entities('attempts', filter=f"PartitionKey eq '{exercise}'") 
    df=pd.DataFrame(items)
    df['question'] = pd.to_numeric(df['question'])
    # Step 4 construct dataframe to send to html page
    if not df.empty:
        df1=df.copy().groupby(['team','question']).agg({'correct':'max'}).reset_index()
        df2=df1.pivot_table(index='team',columns='question',values='correct').reset_index()
        df2['score']=df2.iloc[:,1:].sum(axis=1)
        df1=df.copy().groupby(['team','question'])['answer'].count().reset_index()
        df3=df1.copy().pivot_table(index='team',columns='question').reset_index()

    # rbb set dummy holders
    else:
        df2 = df
        df3 = df

    return render_template("exercise_review.html",title='Exercise Review',user=session["user"],tables=[df2.to_html(classes='data',index=False),df3.to_html(classes='data',index=False)], exercise=exercise)


@classroom_bp.route("/exercise_review_log/<exercise>/<questionnum>")
def exercise_review_open(exercise,questionnum):
    """Exercise Review shows all the students and their progress on an Exercise"""
    user_name = ich.check_user_session(session)

    course_name=str(exercise).split('_')[0]   
    # User Auth Checks
    if not ich.check_authorized_user(session, course_name):
        return redirect(url_for("auth_bp.login"))
     
    # Step 2 get the exercise Structure
    container=init_cosmos('quiz',DATABASE)
    #Query quizes in cosmosdb to get the structure for this assignment
    query = "SELECT * FROM c where c.id=@id"
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

    # Step 3 get all the attempts made for that exercise
    table_service = TableService(account_name=Keys.account_name, account_key=Keys.storage_key)
    tasks = table_service.query_entities('attempts', filter=f"PartitionKey eq '{exercise}'") 
    df=pd.DataFrame(tasks)
    # Step 4 construct dataframe to send to html page
    # rbb handle empty dataframes

    if not df.empty:
        df2 = df[df.question==questionnum]
    else:
        df2 = df

    return render_template("exercise_review.html",title='Exercise Review',user=session["user"],tables=[df2.to_html(classes='data',index=False)], exercise=exercise)


@classroom_bp.route("/exercise_form/<class_val>/<module_val>",methods=['GET'])
def exercise_form(class_val, module_val):
    """Exercise Form"""
    #Step 1 get user information
    user_name = ich.check_user_session(session)
    # Step 2 get the exercise Structure
    container=init_cosmos('quiz',DATABASE)
    #Query quizes in cosmosdb to get the structure for this assignment
    query = """
        SELECT
        *
        FROM c 
        where c.class = @class_val
        and c.module = @module_val
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
 
    items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
    )

    print(items)

    if len(items)==0:
        return f"No assignment found with the name of {class_val + module_val}"
    qnum=len(items[0]['questions'])
    #step 3 create form for that exercise
    class A(FlaskForm):
        a1 = StringField("Question Label")
    
    class B(FlaskForm):
        q=FieldList(FormField(A), min_entries=qnum)
        s=SubmitField("Submit Form")

    form=B()

    return render_template("exercise_form.html",form=form)

@classroom_bp.route("/studentcenter",methods=['GET','POST'])
def student_center():
    items=[]

    user_name = ich.check_user_session(session)
    
    #Test if user is an authorized user
    user_name=session['user'].get('preferred_username').split('@')[0]

    if request.method=='POST':
        #Get course name
        class_name=request.form['wg1']
        #Get quiz format from Cosmos
        container=init_cosmos('quiz',DATABASE)
        query = f"SELECT * FROM c where c.class='{class_name.lower()}' ORDER BY c.module"
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


# rbb 8/19 may want to add an API key to override general workflow managed by session variables
@classroom_bp.route("/add_user",methods=['POST', 'GET'])
def add_user(userId = 'testuser123'):

    user_name = ich.check_user_session(session)

    #if ich.check_permissions(user_name, 'create_user'):
    container=init_cosmos('users',DATABASE)
    container.upsert_item({
        'id' : userId,
        'userId' : userId,
        'name' : 'test user2',
        'role' : 'user',
        'class_access' : [
            'pmap',
        ],
    })
    
    # this should probably just be called as a post. return success or failure as status
    #else:
    #    return 0

# rbb 8/18 need a route to authorize a user for a class, or module and deny
@classroom_bp.route("/authorize_user/<user_id>/<class_val>",methods=['POST'])
def authorize_user(user_id, class_val):

    user_name = ich.check_user_session(session)

    # needs to appropriate handle status codes and check for errors
    if ich.check_permissions(user_name, 'authorize_user'):
        container=init_cosmos('users',DATABASE)
        user = container.read_item(item=user_id, partition_key=user_id)
        user['class_access'].append(class_val)
        container.replace_item(item=user, body=user)

        return 200
    
    else:
        return 301

def deny_user(user, class_val, module):

    user_name = ich.check_user_session(session)

    if ich.check_permissions(user_name, 'deny_user'):
        container=init_cosmos('users',DATABASE)
        user = container.read_item(item=user_name, partition_key=user_name)
        user['class_access'].remove(class_val)
        container.replace_item(item=user, body=user)
    return 0

# rbb 8/18 need a route to update questions
@classroom_bp.route("/update_question",methods=['POST'])
def update_question():

    #user_name = ich.check_user_session(session)
    data = json.loads(request.get_json())
    try:
        class_val = data['class_val']
        module_val = data['module_val']
        question_val = data['question']
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

    print(parameters)
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
            break

    container.replace_item(item=result[0]['id'], body=result[0])

    return "success", 200
    
    #else:
    #    return 301

# rbb 8/18 need a route to add quizzes
def add_quiz():
    return 0
