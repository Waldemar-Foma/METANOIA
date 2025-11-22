from datetime import datetime, timedelta

class LicenseManager:
    def __init__(self, db):
        self.db = db
    
    def get_license(self, therapist_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT therapist_id, license_type, is_active, test_passed, test_score, test_date, license_expires, created_date
            FROM therapist_licenses WHERE therapist_id = ?
        ''', (therapist_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            from .user_models import TherapistLicense
            # Конвертируем строки в datetime объекты
            test_date = datetime.fromisoformat(row[5]) if row[5] else None
            license_expires = datetime.fromisoformat(row[6]) if row[6] else None
            created_date = datetime.fromisoformat(row[7]) if row[7] else None
            
            return TherapistLicense(
                therapist_id=row[0],
                license_type=row[1],
                is_active=bool(row[2]),
                test_passed=bool(row[3]),
                test_score=row[4],
                test_date=test_date,
                license_expires=license_expires,
                created_date=created_date
            )
        return None
    
    def create_license(self, therapist_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO therapist_licenses 
            (therapist_id, license_type, is_active, test_passed, test_score, test_date, license_expires)
            VALUES (?, 'basic', 0, 0, 0, NULL, NULL)
        ''', (therapist_id,))
        conn.commit()
        conn.close()
        return self.get_license(therapist_id)
    
    def update_license_after_test(self, therapist_id, test_score, passed):
        license_expires = datetime.now() + timedelta(days=365)  # Лицензия на 1 год
        test_date = datetime.now()
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE therapist_licenses 
            SET test_passed = ?, test_score = ?, test_date = ?, license_expires = ?, is_active = ?
            WHERE therapist_id = ?
        ''', (passed, test_score, test_date.isoformat(), license_expires.isoformat(), passed, therapist_id))
        conn.commit()
        conn.close()
        
        return self.get_license(therapist_id)
    
    def is_therapist_licensed(self, therapist_id):
        license = self.get_license(therapist_id)
        if not license:
            license = self.create_license(therapist_id)
        return license.is_valid()
    
    def can_retake_test(self, therapist_id):
        """Проверяет, можно ли пересдавать тест (если до окончания лицензии меньше недели)"""
        license = self.get_license(therapist_id)
        if not license or not license.is_valid():
            return True
        
        if not license.license_expires:
            return True
        
        days_until_expiry = license.days_until_expiry()
        return days_until_expiry is not None and days_until_expiry <= 7
