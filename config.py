import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('AXL_WINNER') or 'dev-secret-key-change-in-production'
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Роли пользователей
    USER_ROLES = {
        'patient': 'patient',
        'therapist': 'therapist', 
        'admin': 'admin',
        'superadmin': 'superadmin'
    }
