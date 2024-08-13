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

# rbb setting for testing without authentication
TESTING_MODE = Config.TESTING

ClassGroups=sorted(['PMAP','CDA','FHIR','OHDSI'])

answerkey=load_answerkey('quiz','bids-class')

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
    if request.method=='GET':
        form=AnswerForm()
        return render_template('answerform.html',title='AnswerForm',form=form)
    sub_fields=['module', 'team', 'question_num', 'answer_num']
    for field in sub_fields:
        if field not in request.form.keys():
            return jsonify({"message":"Bad request, missing field {}".format(field)}),400
    # Get the answer key
    if 'class' in request.form.keys():
        #removing use of class as a variable name
        partition_key=request.form['class']
    else:
        partition_key=request.form['class_name']
    module_num=request.form['module']
    module_name=partition_key+"_"+ module_num
    
    

    #container=init_cosmos('quiz','bids-class')
    #output=container.read_item(item=item_name,partition_key=partition_key)
    #questions=output['questions']
  
    question_num=int(request.form['question_num'])
    answer_num=request.form['answer_num']

    if module_name in answerkey.keys():
        questions=answerkey[module_name]  

    #Logging - Get the max RowKey and increment to make unique
    table_service = TableService(account_name=Keys.account_name, account_key=Keys.storage_key)
    RowKey=str(len(list(table_service.query_entities('attempts')))+1)

    attempt={'PartitionKey':module_name,
            'RowKey':RowKey,
            'course':partition_key,
            'module': module_name,
            'team': request.form['team'],
            'question': question_num,
            'answer':str(answer_num)
    } 

    #Checks to see if its an open question, if it is empty answer_num so it will return tru
    #Note the attempt dictionary already logged the actual answer  
    if len(questions[question_num])==0:
        answer_num=""  

    if str(questions[question_num])==str(answer_num):        
        #Log success for team
        nextquestion=''
        attempt['correct']=1
        table_service.insert_or_replace_entity('attempts',attempt)
        return jsonify({"Message":"Great job! You got it right.","Next Question":nextquestion}),200
    else:
        #Log failure for team
        attempt['correct']=0
        table_service.insert_or_replace_entity('attempts',attempt)
        return jsonify({"message":"Sorry, wrong answer"}),406  
    return jsonify({"Something went wrong"}),400



@classroom_bp.route("/assignment/<exercise>")
def assignment(exercise):
    """Assignment home"""
    # for testing 
    session, user_name = ich.check_user_session(session)

    container=init_cosmos('quiz','bids-class')
    #Query quizes in cosmosdb to get the structure for this assignment
    # rbb double check that this doesn't open to sql injection
    query = "SELECT * FROM c where c.id='{}'".format(exercise.lower())
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True )) 
    if len(items)==0:
        return "No assignment found with the name of {}".format(exercise)
    
    assignment=items[0]['questions']

    #Query Tableservice to get all attempts to answer questions for this assignment
    table_service = TableService(account_name=Keys.account_name, account_key=Keys.storage_key)
    tasks = table_service.query_entities('attempts', filter=f"team eq '{user_name}'") 
    df=pd.DataFrame(tasks)

    # rbb we'll check to see if something is returned at all, and if it is, flag
    # where it has been attempted 
    attempted = True
    if not df.empty:
        df=df[df['PartitionKey']=="{}".format(exercise.lower())]        
    if df.empty:
        attempted = False

    qnum,anum=0,0
    # rbb i think this should just be changed to enumerate? prevent missing indices
    for i in range(0,len(assignment)):
        q_num=assignment[i]['question_num']
        attempts=len(df[df.question==str(q_num)]) if attempted else 0
        correct=len(df[(df.question==str(q_num))&(df.correct==1)])>0 if attempted else 0
        assignment[i]['attempts']=attempts
        assignment[i]['correct']=correct
        qnum+=1
        if correct==True:
            anum+=1
    df1=pd.DataFrame(assignment)
    df1.drop('correct_answer',axis=1, inplace=True)
    df1.sort_values('question_num',inplace=True)
    df1.reset_index(drop=True,inplace=True)
    return render_template("assignment.html",title='Assignment',user=session["user"],tables=[df1.to_html(classes='data',index=False)], exercise=exercise,qnum=qnum,anum=anum)

@classroom_bp.route("/exercise_review/<exercise>")
def exercise_review(exercise):
    """Exercise Review shows all the students and their progress on an Exercise"""
    session, user_name = ich.check_user_session(session)

    course_name=str(exercise).split('_')[0]   

    if not ich.check_authorized_user(session, course_name):
        return redirect(url_for("auth_bp.login"))
     
    # Step 2 get the exercise Structure
    container=init_cosmos('quiz','bids-class')
    #Query quizes in cosmosdb to get the structure for this assignment
    query = "SELECT * FROM c where c.id='{}'".format(exercise.lower())
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True )) 
    if len(items)==0:
        return "No assignment found with the name of {}".format(exercise)
    
    # Step 3 get all the attempts made for that exercise
    table_service = TableService(account_name=Keys.account_name, account_key=Keys.storage_key)
    tasks = table_service.query_entities('attempts', filter=f"PartitionKey eq '{exercise}'") 
    df=pd.DataFrame(tasks)
    # Step 4 construct dataframe to send to html page
    if not df.empty:
        df1=df.groupby(['team','question']).agg({'correct':'max'}).reset_index()
        df2=df1.pivot_table(index='team',columns='question',values='correct').reset_index()
        df2['score']=df2.iloc[:,1:].sum(axis=1)
        df1=df.groupby(['team','question'])['answer'].count().reset_index()
        df3=df1.pivot_table(index='team',columns='question')

    return render_template("exercise_review.html",title='Exercise Review',user=session["user"],tables=[df2.to_html(classes='data',index=False),df3.to_html(classes='data',index=False)], exercise=exercise)


@classroom_bp.route("/exercise_review_log/<exercise>/<questionnum>")
def exercise_review_open(exercise,questionnum):
    """Exercise Review shows all the students and their progress on an Exercise"""
    session, user_name = ich.check_user_session(session)

    course_name=str(exercise).split('_')[0]   
    # User Auth Checks
    if not ich.check_authorized_user(session, course_name):
        return redirect(url_for("auth_bp.login"))
     
    # Step 2 get the exercise Structure
    container=init_cosmos('quiz','bids-class')
    #Query quizes in cosmosdb to get the structure for this assignment
    # TODO *RBB 7/26 - Parameterize Queries 
    query = "SELECT * FROM c where c.id='{}'".format(exercise.lower())
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True )) 
    if len(items)==0:
        return "No assignment found with the name of {}".format(exercise)

    # Step 3 get all the attempts made for that exercise
    table_service = TableService(account_name=Keys.account_name, account_key=Keys.storage_key)
    tasks = table_service.query_entities('attempts', filter=f"PartitionKey eq '{exercise}'") 
    df=pd.DataFrame(tasks)
    # Step 4 construct dataframe to send to html page
    # rbb handle empty dataframes

    df2 = df[df.question==questionnum] if not df.empty else df2 = df

    return render_template("exercise_review.html",title='Exercise Review',user=session["user"],tables=[df2.to_html(classes='data',index=False)], exercise=exercise)


@classroom_bp.route("/exercise_form/<exercise>",methods=['GET','POST'])
def exercise_form(exercise):
    """Exercise Form"""
    #Step 1 get user information
    session, user_name = ich.check_user_session(session)
        
    course_name=str(exercise).split('_')[0]
    # Step 2 get the exercise Structure
    container=init_cosmos('quiz','bids-class')
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

    session, user_name = ich.check_user_session(session)
    
    #Test if user is an authorized user
    user_name=session['user'].get('preferred_username').split('@')[0]

    if request.method=='POST':
        #Get course name
        class_name=request.form['wg1']
        #Get quiz format from Cosmos
        container=init_cosmos('quiz','bids-class')
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

   

