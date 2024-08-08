from informatics_classroom.config import Keys, Config
from flask import request, redirect, url_for


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