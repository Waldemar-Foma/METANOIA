from .database import Database
from .user_models import UserManager
from .therapy_models import TherapyDataManager
from .license_manager import LicenseManager
from .test_manager import TestManager

class DataManager:
    def __init__(self, db_path='data/vr_therapy.db'):
        self.db = Database(db_path)
        self.user_manager = UserManager(self.db)
        self.therapy_manager = TherapyDataManager(self.db)
        self.license_manager = LicenseManager(self.db)
        self.test_manager = TestManager(self.db)
    
    def get_patient_with_sessions(self, patient_id):
        patient = self.user_manager.get_user_by_id(patient_id)
        if patient and patient.role == 'patient':
            sessions = self.therapy_manager.get_sessions_by_patient(patient_id)
            return patient, sessions
        return None, []
    
    def get_all_patients_with_sessions(self):
        # Получаем всех пациентов текущего терапевта (пока используем TH001 для демо)
        patients = self.user_manager.get_patients_by_therapist("TH001")
        result = []
        for patient in patients:
            sessions = self.therapy_manager.get_sessions_by_patient(patient.user_id)
            result.append((patient, sessions))
        return result
    
    def get_patients_by_therapist_id(self, therapist_id):
        """Получить пациентов по ID терапевта"""
        patients = self.user_manager.get_patients_by_therapist(therapist_id)
        result = []
        for patient in patients:
            sessions = self.therapy_manager.get_sessions_by_patient(patient.user_id)
            result.append((patient, sessions))
        return result
    
    def calculate_average_sud_reduction(self):
        all_sessions = self.therapy_manager.get_all_sessions()
        if not all_sessions:
            return 0
        
        total_reduction = 0
        for session in all_sessions:
            total_reduction += (session.post_sud - session.pre_sud)
        
        return total_reduction / len(all_sessions)