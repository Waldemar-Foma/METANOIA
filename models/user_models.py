from datetime import datetime, timedelta
import secrets
import string

class User:
    def __init__(self, user_id, username, password_hash, role, name, therapist_id=None, is_active=True, created_date=None):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.name = name
        self.therapist_id = therapist_id
        self.is_active = is_active
        
        # Конвертируем created_date в datetime объект если это строка
        if isinstance(created_date, str):
            try:
                self.created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.created_date = datetime.now()
        else:
            self.created_date = created_date or datetime.now()
    
    @staticmethod
    def generate_credentials():
        """Генерация логина и пароля для пациентов"""
        username = 'pt' + ''.join(secrets.choice(string.digits) for _ in range(6))
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        return username, password
    
    @staticmethod
    def generate_therapist_credentials():
        """Генерация логина и пароля для терапевтов"""
        username = 'doc' + ''.join(secrets.choice(string.digits) for _ in range(4))
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        return username, password

class TherapistLicense:
    def __init__(self, therapist_id, license_type='basic', is_active=False, test_passed=False, 
                 test_score=0, test_date=None, license_expires=None, created_date=None):
        self.therapist_id = therapist_id
        self.license_type = license_type
        self.is_active = is_active
        self.test_passed = test_passed
        self.test_score = test_score
        
        # Конвертируем даты из строк в datetime объекты
        if isinstance(test_date, str):
            try:
                self.test_date = datetime.fromisoformat(test_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.test_date = None
        else:
            self.test_date = test_date
            
        if isinstance(license_expires, str):
            try:
                self.license_expires = datetime.fromisoformat(license_expires.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.license_expires = None
        else:
            self.license_expires = license_expires
            
        if isinstance(created_date, str):
            try:
                self.created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.created_date = datetime.now()
        else:
            self.created_date = created_date or datetime.now()
    
    def is_valid(self):
        if not self.is_active or not self.test_passed:
            return False
        if self.license_expires and datetime.now() > self.license_expires:
            return False
        return True
    
    def days_until_expiry(self):
        if not self.license_expires:
            return None
        delta = self.license_expires - datetime.now()
        return delta.days

class UserManager:
    def __init__(self, db):
        self.db = db
        # Временное хранилище для паролей (в продакшене использовать безопасное хранилище)
        self.temp_passwords = {}
    
    def get_user_by_username(self, username):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, password_hash, role, name, therapist_id, is_active, created_date
            FROM users WHERE username = ? AND is_active = 1
        ''', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(*row)
        return None
    
    def get_user_by_id(self, user_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, password_hash, role, name, therapist_id, is_active, created_date
            FROM users WHERE user_id = ? AND is_active = 1
        ''', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(*row)
        return None
    
    def get_patients_by_therapist(self, therapist_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, password_hash, role, name, therapist_id, is_active, created_date
            FROM users WHERE therapist_id = ? AND role = 'patient' AND is_active = 1
        ''', (therapist_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [User(*row) for row in rows]
    
    def create_patient(self, name, therapist_id):
        username, password = User.generate_credentials()
        user_id = f"PT{self.get_next_patient_id():03d}"
        password_hash = self.db.hash_password(password)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, password_hash, role, name, therapist_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, password_hash, 'patient', name, therapist_id))
        conn.commit()
        conn.close()
        
        # Сохраняем пароль во временном хранилище
        self.temp_passwords[user_id] = password
        
        patient = self.get_user_by_id(user_id)
        return patient, username, password
    
    def get_patient_password(self, patient_id):
        """Получить пароль пациента (только для что созданных)"""
        return self.temp_passwords.get(patient_id)
    
    def create_therapist(self, name):
        """Создание терапевта (для суперадмина)"""
        username, password = User.generate_therapist_credentials()
        user_id = f"TH{self.get_next_therapist_id():03d}"
        password_hash = self.db.hash_password(password)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, password_hash, role, name)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, password_hash, 'therapist', name))
        conn.commit()
        conn.close()
        
        therapist = self.get_user_by_id(user_id)
        return therapist, username, password
    
    def get_next_patient_id(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'patient'")
        count = cursor.fetchone()[0]
        conn.close()
        return count + 1
    
    def get_next_therapist_id(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'therapist'")
        count = cursor.fetchone()[0]
        conn.close()
        return count + 1
    
    def verify_password(self, user, password):
        return self.db.verify_password(password, user.password_hash)