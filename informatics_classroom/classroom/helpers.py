from informatics_classroom.config import Keys, Config
from flask import request, redirect, url_for
from informatics_classroom.azure_func import init_cosmos,load_answerkey


def check_user_session(session):
    if Config.TESTING:
        session['user'] = 'user_testing'
        user_name = session['user']
    else:
        if not session.get("user"):
            #Test if user session is set
            return redirect(url_for("auth_bp.login"))
        if not session['user'].get('preferred_username').split('@')[1][:2]==Keys.auth_domain:
            #Test if authenticated user is coming from an authorized domain
            return redirect(url_for("auth_bp.login"))
        #Test if user is an authorized user

    user_name=session['user'].get('preferred_username').split('@')[0]

    return session, user_name

def check_authorized_user(session, course_name):
    authorized_user=False   
    if Config.TESTING:
            authorized_user = True
    else:
        user_name=session['user'].get('preferred_username').split('@')[0]

        container=init_cosmos('quiz','bids-class')
        items=container.read_item(item="auth_users",partition_key="auth")

        for name in items['users']:
            if user_name in name:
            # Test if user is in list of authorized users
                if course_name in name[user_name]:
                    authorized_user=True
    
    return authorized_user