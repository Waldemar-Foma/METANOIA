from datetime import datetime

class Session:
    def __init__(self, session_id, patient_id, date, duration_minutes, module_used, pre_sud, post_sud, parameters=None):
        self.session_id = session_id
        self.patient_id = patient_id
        self.date = date
        self.duration_minutes = duration_minutes
        self.module_used = module_used
        self.pre_sud = pre_sud
        self.post_sud = post_sud
        self.parameters = parameters or {}
    
    def to_dict(self):
        return {
            'session_id': self.session_id,
            'patient_id': self.patient_id,
            'date': self.date,
            'duration_minutes': self.duration_minutes,
            'module_used': self.module_used,
            'pre_sud': self.pre_sud,
            'post_sud': self.post_sud,
            'parameters': self.parameters
        }

class TherapyDataManager:
    def __init__(self, db):
        self.db = db
    
    def get_sessions_by_patient(self, patient_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, patient_id, date, duration_minutes, module_used, pre_sud, post_sud, parameters
            FROM therapy_sessions WHERE patient_id = ? ORDER BY date
        ''', (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            sessions.append(Session(*row))
        return sessions
    
    def get_all_sessions(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, patient_id, date, duration_minutes, module_used, pre_sud, post_sud, parameters
            FROM therapy_sessions ORDER BY date
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            sessions.append(Session(*row))
        return sessions
    
    def get_patient_preferences(self, patient_id):
        patient_sessions = self.get_sessions_by_patient(patient_id)
        if not patient_sessions:
            return {}
        
        module_counts = {}
        safe_place_prefs = {}
        
        for session in patient_sessions:
            module = session.module_used
            module_counts[module] = module_counts.get(module, 0) + 1
            
            if "Безопасное место" in module:
                place = module.split(" - ")[-1] if " - " in module else "default"
                safe_place_prefs[place] = safe_place_prefs.get(place, 0) + 1
        
        return {
            'favorite_module': max(module_counts, key=module_counts.get) if module_counts else "EMDR",
            'module_counts': module_counts,
            'safe_place_preferences': safe_place_prefs,
            'total_sessions': len(patient_sessions),
            'avg_sud_reduction': sum(s.post_sud - s.pre_sud for s in patient_sessions) / len(patient_sessions)
        }