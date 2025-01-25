from informatics_classroom.config import Keys, Config
from flask import request, redirect, url_for
from informatics_classroom.azure_func import init_cosmos,load_answerkey


def check_user_session(session):
    if Config.TESTING:
        session['user'] = {'preferred_username' : 'rbarre16'}	
        session['user_name'] = session['user'].get('preferred_username')
        return True
    else:
        try:
            if not session.get("user"):
                #Test if user session is set
                return False
            #if not session['user'].get('preferred_username').split('@')[1][:2]==Keys.auth_domain:
                #Test if authenticated user is coming from an authorized domain
            #    return False
        except:
            session.clear()
            return False

        #Test if user is an authorized user

    session['user_name']=session['user'].get('preferred_username').split('@')[0]

    return True

def check_authorized_user(session, course_name):

    if Config.TESTING:
        return True
    else:
        container=init_cosmos('quiz',Config.DATABASE)
        items=container.read_item(item="auth_users",partition_key="auth")

        for name in items['users']:
            if session.get('user_name') in name:
            # Test if user is in list of authorized users
                if course_name in name[session.get('user_name')]:
                    return True
                
    return False

# rbb 8/18 route to check if a user is allowed certain permissions based on their role
def check_permissions(user_id, action):

    container=init_cosmos('users',Config.DATABASE)
    user = container.read_item(item=user_id, partition_key=user_id)
    if action in user['permissions']:
        return 1
    
    return 0