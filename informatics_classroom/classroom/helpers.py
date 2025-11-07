from informatics_classroom.config import Keys, Config
from flask import request, redirect, url_for


def check_user_session(session):
    if Config.TESTING:
        session['user'] = {'preferred_username' : 'rbarre16@jh.edu'}
        session['user_name'] = session['user'].get('preferred_username')
        return True
    else:
        try:
            if not session.get("user"):
                #Test if user session is set
                return False
            if not session['user'].get('preferred_username').split('@')[1][:2]==Keys.auth_domain:
                #Test if authenticated user is coming from an authorized domain
                return False
        except:
            session.clear()
            return False

        #Test if user is an authorized user

    session['user_name']=session['user'].get('preferred_username').split('@')[0]

    return True