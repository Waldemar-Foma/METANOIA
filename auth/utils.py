from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def therapist_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'therapist':
            flash('Доступ только для терапевтов', 'error')
            return redirect(url_for('patient_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'patient':
            flash('Доступ только для пациентов', 'error')
            return redirect(url_for('therapist_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def is_therapist():
    return session.get('role') == 'therapist'

def is_patient():
    return session.get('role') == 'patient'

def is_superadmin():
    return session.get('role') == 'superadmin'

def get_current_user():
    from models.data_manager import DataManager
    data_manager = DataManager()
    return data_manager.user_manager.get_user_by_id(session['user_id'])

def hash_password(password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    return hash_password(password) == password_hash