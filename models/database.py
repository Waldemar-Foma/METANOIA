import sqlite3
import os
from datetime import datetime, timedelta
import hashlib
import secrets
import string
import json

class Database:
    def __init__(self, db_path='data/vr_therapy.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                name TEXT NOT NULL,
                therapist_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (therapist_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица лицензий терапевтов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS therapist_licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                therapist_id TEXT NOT NULL,
                license_type TEXT DEFAULT 'basic',
                is_active BOOLEAN DEFAULT 0,
                test_passed BOOLEAN DEFAULT 0,
                test_score INTEGER DEFAULT 0,
                test_date TIMESTAMP,
                license_expires TIMESTAMP,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (therapist_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица сессий терапии
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS therapy_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                patient_id TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_minutes INTEGER NOT NULL,
                module_used TEXT NOT NULL,
                pre_sud INTEGER NOT NULL,
                post_sud INTEGER NOT NULL,
                parameters TEXT,
                FOREIGN KEY (patient_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица тестовых вопросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                options TEXT NOT NULL, -- JSON массив вариантов
                correct_answer INTEGER NOT NULL, -- индекс правильного ответа
                explanation TEXT,
                question_type TEXT DEFAULT 'theory'
            )
        ''')
        
        # Вставляем демо-данные
        self.insert_sample_data(cursor)
        conn.commit()
        conn.close()
    
    def insert_sample_data(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            from datetime import datetime, timedelta
            
            # Добавляем суперадмина
            superadmin = [
                ('SA001', 'superadmin', self.hash_password('admin123'), 'superadmin', 'Системный Администратор')
            ]
            
            for admin in superadmin:
                cursor.execute('''
                    INSERT INTO users (user_id, username, password_hash, role, name)
                    VALUES (?, ?, ?, ?, ?)
                ''', admin)
            
            # Добавляем терапевтов
            therapists = [
                ('TH001', 'therapist', self.hash_password('therapy123'), 'therapist', 'Др. Смирнова'),
                ('TH002', 'doctor2', self.hash_password('doctor123'), 'therapist', 'Др. Петров'),
                ('TH003', 'licensed_doc', self.hash_password('license123'), 'therapist', 'Др. Козлова')
            ]
            
            for therapist in therapists:
                cursor.execute('''
                    INSERT INTO users (user_id, username, password_hash, role, name)
                    VALUES (?, ?, ?, ?, ?)
                ''', therapist)
            
            # Добавляем пациентов
            patients = [
                ('PT001', 'pt001234', self.hash_password('pass123'), 'patient', 'Иван Петров', 'TH001'),
                ('PT002', 'pt002345', self.hash_password('pass123'), 'patient', 'Мария Сидорова', 'TH001'),
                ('PT003', 'pt003456', self.hash_password('pass123'), 'patient', 'Алексей Иванов', 'TH002'),
                ('PT004', 'pt004567', self.hash_password('pass123'), 'patient', 'Елена Васильева', 'TH003')
            ]
            
            for patient in patients:
                cursor.execute('''
                    INSERT INTO users (user_id, username, password_hash, role, name, therapist_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', patient)
            
            # Добавляем тестовые вопросы (ИСПРАВЛЕННЫЕ JSON)
            questions = [
                {
                    'question_text': 'Что такое контролируемая экспозиция в VR-терапии ПТСР?',
                    'options': '["Полное погружение в травмирующую ситуацию", "Постепенное воздействие на пациента в безопасной среде", "Избегание любых напоминаний о травме", "Медикаментозное лечение"]',
                    'correct_answer': 1,
                    'explanation': 'Контролируемая экспозиция - это постепенное воздействие на пациента элементами травмирующей ситуации в безопасной контролируемой среде VR.',
                    'question_type': 'theory'
                },
                {
                    'question_text': 'Что делать при резком повышении SUD (субъективной единицы дистресса) у пациента во время сессии?',
                    'options': '["Продолжить сессию", "Немедленно перейти к модулю \\"Безопасное место\\"", "Увеличить интенсивность стимулов", "Прервать сессию без последующих действий"]',
                    'correct_answer': 1,
                    'explanation': 'При резком повышении SUD необходимо немедленно перевести пациента в безопасное место для стабилизации состояния.',
                    'question_type': 'emergency'
                },
                {
                    'question_text': 'Какой частотный диапазон используется в EMDR-модуле?',
                    'options': '["0.1-0.5 Гц", "1-4 Гц", "5-10 Гц", "10-20 Гц"]',
                    'correct_answer': 1,
                    'explanation': 'В EMDR-терапии используется частота 1-4 Гц для билатеральной стимуляции.',
                    'question_type': 'technical'
                },
                {
                    'question_text': 'Что означает кнопка экстренной остановки?',
                    'options': '["Пауза сессии", "Перезагрузка системы", "Мгновенное прекращение всех стимулов", "Смена сцены"]',
                    'correct_answer': 2,
                    'explanation': 'Кнопка экстренной остановки мгновенно прекращает все стимулы и переводит систему в безопасный режим.',
                    'question_type': 'emergency'
                },
                {
                    'question_text': 'Как часто нужно обновлять лицензию терапевта VR-терапии?',
                    'options': '["Каждый месяц", "Каждые 6 месяцев", "Каждый год", "Каждые 2 года"]',
                    'correct_answer': 2,
                    'explanation': 'Лицензия терапевта VR-терапии требует ежегодного обновления через прохождение тестирования.',
                    'question_type': 'administrative'
                }
            ]
            
            for q in questions:
                cursor.execute('''
                    INSERT INTO test_questions (question_text, options, correct_answer, explanation, question_type)
                    VALUES (?, ?, ?, ?, ?)
                ''', (q['question_text'], q['options'], q['correct_answer'], q['explanation'], q['question_type']))
            
            # Добавляем лицензии для терапевтов
            license_expires = datetime.now() + timedelta(days=365)
            
            licenses = [
                ('TH001', 'basic', 0, 0, 0, None, None),
                ('TH002', 'basic', 0, 0, 0, None, None),
                ('TH003', 'premium', 1, 1, 95, datetime.now().isoformat(), license_expires.isoformat())
            ]
            
            for license_data in licenses:
                cursor.execute('''
                    INSERT INTO therapist_licenses 
                    (therapist_id, license_type, is_active, test_passed, test_score, test_date, license_expires)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', license_data)
            
            # Добавляем демо-сессии
            sessions = [
                ('SES_PT001_1', 'PT001', '2024-01-10 10:00:00', 30, '360° Экспозиция', 7, 4),
                ('SES_PT001_2', 'PT001', '2024-01-15 11:00:00', 35, 'EMDR', 6, 3),
                ('SES_PT001_3', 'PT001', '2024-01-20 09:30:00', 40, 'Безопасное место - Море', 5, 2),
                ('SES_PT002_1', 'PT002', '2024-01-12 14:00:00', 30, '360° Экспозиция', 8, 5),
                ('SES_PT002_2', 'PT002', '2024-01-18 15:00:00', 35, 'Безопасное место - Лес', 7, 4),
                ('SES_PT003_1', 'PT003', '2024-01-14 16:00:00', 30, 'EMDR', 6, 3),
                ('SES_PT004_1', 'PT004', '2024-01-16 09:00:00', 45, '360° Экспозиция', 6, 2),
                ('SES_PT004_2', 'PT004', '2024-01-23 10:00:00', 50, 'EMDR', 5, 1),
                ('SES_PT004_3', 'PT004', '2024-01-30 11:00:00', 40, 'Безопасное место - Горы', 4, 1)
            ]
            
            for session in sessions:
                cursor.execute('''
                    INSERT INTO therapy_sessions (session_id, patient_id, date, duration_minutes, module_used, pre_sud, post_sud)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', session)
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password, password_hash):
        return self.hash_password(password) == password_hash