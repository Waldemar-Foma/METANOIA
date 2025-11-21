from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from config import Config
from models.data_manager import DataManager
from auth.auth import login_required, therapist_required, patient_required
from auth.utils import get_current_user, is_therapist, is_patient, is_superadmin
import json
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
data_manager = DataManager()

# Маршруты аутентификации
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if is_therapist():
        return redirect(url_for('therapist_dashboard'))
    elif is_patient():
        return redirect(url_for('patient_dashboard'))
    elif is_superadmin():
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Валидация входных данных
        if not username or not password:
            flash('Пожалуйста, заполните все поля', 'error')
            return render_template('auth/login.html')
        
        user = data_manager.user_manager.get_user_by_username(username)
        
        if user:
            if data_manager.user_manager.verify_password(user, password):
                # Успешный вход
                session['user_id'] = user.user_id
                session['username'] = user.username
                session['role'] = user.role
                session['name'] = user.name
                session.permanent = True
                
                # Проверяем лицензию для терапевтов
                if user.role == 'therapist':
                    license_info = data_manager.license_manager.get_license(user.user_id)
                    session['is_licensed'] = license_info.is_valid() if license_info else False
                    if license_info and license_info.license_expires:
                        session['license_expires'] = license_info.license_expires.isoformat()
                
                flash(f'Добро пожаловать, {user.name}!', 'success')
                
                # Перенаправление в зависимости от роли
                if user.role == 'therapist':
                    return redirect(url_for('therapist_dashboard'))
                elif user.role == 'superadmin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('patient_dashboard'))
            else:
                flash('Неверный пароль', 'error')
        else:
            flash('Пользователь с таким логином не найден', 'error')
    
    return render_template('auth/login.html')

@app.route('/therapist-login')
def therapist_login():
    return render_template('auth/therapist_login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# Маршруты суперадмина
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not is_superadmin():
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    # Получаем всех пользователей
    all_users = []
    conn = data_manager.db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, role, name, is_active FROM users')
    for row in cursor.fetchall():
        all_users.append({
            'user_id': row[0],
            'username': row[1],
            'role': row[2],
            'name': row[3],
            'is_active': bool(row[4])
        })
    conn.close()
    
    return render_template('admin/admin_dashboard.html', users=all_users)

@app.route('/admin/users/toggle/<user_id>')
@login_required
def toggle_user_status(user_id):
    if not is_superadmin():
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    conn = data_manager.db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT is_active FROM users WHERE user_id = ?', (user_id,))
    current_status = cursor.fetchone()[0]
    
    new_status = 0 if current_status else 1
    cursor.execute('UPDATE users SET is_active = ? WHERE user_id = ?', (new_status, user_id))
    conn.commit()
    conn.close()
    
    status_text = "активирован" if new_status else "деактивирован"
    flash(f'Пользователь {status_text}', 'success')
    return redirect(url_for('admin_dashboard'))

# Маршруты терапевта
@app.route('/therapist/dashboard')
@therapist_required
def therapist_dashboard():
    therapist_id = session['user_id']
    license_info = data_manager.license_manager.get_license(therapist_id)
    
    # Если терапевт не лицензирован, показываем только профиль
    if not license_info or not license_info.is_valid():
        flash('Для доступа к полному функционалу необходимо пройти обучение и получить лицензию', 'warning')
        return redirect(url_for('therapist_profile'))
    
    # Лицензированный терапевт видит полную панель
    patients_with_sessions = data_manager.get_patients_by_therapist_id(therapist_id)
    avg_sud_reduction = data_manager.calculate_average_sud_reduction()
    
    # Подсчитываем общее количество сессий
    total_sessions = sum(len(sessions) for patient, sessions in patients_with_sessions)
    
    return render_template('dashboard/therapist_panel.html',
                         patients=patients_with_sessions,
                         average_sud_reduction=avg_sud_reduction,
                         data_manager=data_manager,
                         license_info=license_info,
                         total_sessions=total_sessions)

@app.route('/therapist/profile')
@therapist_required
def therapist_profile():
    therapist_id = session['user_id']
    license_info = data_manager.license_manager.get_license(therapist_id)
    therapist = data_manager.user_manager.get_user_by_id(therapist_id)
    
    return render_template('dashboard/therapist_profile.html',
                         license_info=license_info,
                         therapist=therapist)

@app.route('/therapist/training')
@therapist_required
def therapist_training():
    """Страница обучения и тестирования для терапевтов"""
    return render_template('training/therapist_training.html')

@app.route('/therapist/training/test')
@therapist_required
def therapist_test():
    """Страница тестирования"""
    questions = data_manager.test_manager.get_test_questions()
    return render_template('training/therapist_test.html', questions=questions)

@app.route('/therapist/training/submit-test', methods=['POST'])
@therapist_required
def submit_test():
    """Обработка результатов тестирования"""
    try:
        answers = request.form.to_dict()
        
        if not answers:
            flash('Необходимо ответить на все вопросы теста', 'error')
            return redirect(url_for('therapist_test'))
        
        result = data_manager.test_manager.evaluate_test(answers)
        
        # Обновляем лицензию
        therapist_id = session['user_id']
        updated_license = data_manager.license_manager.update_license_after_test(
            therapist_id, 
            result['score'], 
            result['passed']
        )
        
        # Обновляем сессию
        session['is_licensed'] = updated_license.is_valid()
        if updated_license.license_expires:
            session['license_expires'] = updated_license.license_expires.isoformat()
        
        if result['passed']:
            flash('Поздравляем! Вы успешно прошли тестирование и получили лицензию', 'success')
        else:
            flash(f'Тестирование не пройдено. Ваш результат: {result["score"]}%. Необходимо набрать 80% или выше.', 'warning')
        
        return render_template('training/test_results.html', 
                             result=result,
                             license_info=updated_license)
    
    except Exception as e:
        flash(f'Произошла ошибка при обработке теста: {str(e)}', 'error')
        return redirect(url_for('therapist_test'))

# Управление пациентами - исправленный endpoint
@app.route('/therapist/patients')
@therapist_required
def therapist_patient_management():
    if not session.get('is_licensed'):
        flash('Для доступа к управлению пациентами необходимо пройти обучение и получить лицензию', 'warning')
        return redirect(url_for('therapist_training'))
    
    patients = data_manager.user_manager.get_patients_by_therapist(session['user_id'])
    
    # Создаем словарь с паролями пациентов
    patient_credentials = {}
    for patient in patients:
        password = data_manager.user_manager.get_patient_password(patient.user_id)
        if password:
            patient_credentials[patient.user_id] = password
    
    return render_template('admin/patient_management.html', 
                         patients=patients,
                         patient_credentials=patient_credentials)

@app.route('/therapist/patients/create', methods=['POST'])
@therapist_required
def create_patient():
    if not session.get('is_licensed'):
        flash('Для создания пациентов необходимо пройти обучение и получить лицензию', 'warning')
        return redirect(url_for('therapist_training'))
    
    name = request.form.get('name', '').strip()
    if name:
        try:
            patient, username, password = data_manager.user_manager.create_patient(name, session['user_id'])
            # Теперь показываем реальный пароль, а не звездочки
            flash(f'Пациент {name} создан. Логин: <strong>{username}</strong>, Пароль: <strong>{password}</strong>', 'success')
        except Exception as e:
            flash(f'Ошибка при создании пациента: {str(e)}', 'error')
    else:
        flash('Введите имя пациента', 'error')
    
    return redirect(url_for('therapist_patient_management'))

@app.route('/api/patient/<patient_id>/reset-password', methods=['POST'])
@therapist_required
def reset_patient_password(patient_id):
    """Сброс и генерация нового пароля для пациента"""
    try:
        # Проверяем, что пациент принадлежит текущему терапевту
        patient = data_manager.user_manager.get_user_by_id(patient_id)
        if not patient or patient.therapist_id != session['user_id']:
            return jsonify({'success': False, 'error': 'Пациент не найден или доступ запрещен'}), 403
        
        # Генерируем новый пароль
        import secrets
        import string
        
        new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        new_password_hash = data_manager.db.hash_password(new_password)
        
        # Обновляем пароль в базе данных
        conn = data_manager.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET password_hash = ? WHERE user_id = ?',
            (new_password_hash, patient_id)
        )
        conn.commit()
        conn.close()
        
        # Обновляем временное хранилище
        data_manager.user_manager.temp_passwords[patient_id] = new_password
        
        return jsonify({
            'success': True,
            'new_password': new_password,
            'message': 'Пароль успешно сброшен'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Маршруты пациента
@app.route('/patient/dashboard')
@patient_required
def patient_dashboard():
    try:
        patient, sessions = data_manager.get_patient_with_sessions(session['user_id'])
        preferences = data_manager.therapy_manager.get_patient_preferences(session['user_id'])
        
        return render_template('dashboard/patient_dashboard.html',
                             patient=patient,
                             sessions=sessions,
                             preferences=preferences)
    except Exception as e:
        flash(f'Ошибка при загрузке данных: {str(e)}', 'error')
        return render_template('dashboard/patient_dashboard.html',
                             patient=None,
                             sessions=[],
                             preferences={})

@app.route('/patient/sessions')
@patient_required
def patient_sessions():
    try:
        patient, sessions = data_manager.get_patient_with_sessions(session['user_id'])
        return render_template('dashboard/session_analytics.html',
                             patient=patient,
                             sessions=sessions)
    except Exception as e:
        flash(f'Ошибка при загрузке сессий: {str(e)}', 'error')
        return render_template('dashboard/session_analytics.html',
                             patient=None,
                             sessions=[])

@app.route('/patient/<patient_id>')
@login_required
def patient_detail(patient_id):
    """Детальная страница пациента (для терапевта)"""
    if not is_therapist():
        flash('Доступ запрещен', 'error')
        return redirect(url_for('patient_dashboard'))
    
    if not session.get('is_licensed'):
        flash('Для доступа к данным пациентов необходимо пройти обучение и получить лицензию', 'warning')
        return redirect(url_for('therapist_training'))
    
    try:
        patient, sessions = data_manager.get_patient_with_sessions(patient_id)
        if not patient:
            flash('Пациент не найден', 'error')
            return redirect(url_for('therapist_dashboard'))
        
        preferences = data_manager.therapy_manager.get_patient_preferences(patient_id)
        recommendations = generate_recommendations(patient, preferences)
        
        return render_template('dashboard/patient_detail.html',
                             patient=patient,
                             sessions=sessions,
                             preferences=preferences,
                             recommendations=recommendations)
    except Exception as e:
        flash(f'Ошибка при загрузке данных пациента: {str(e)}', 'error')
        return redirect(url_for('therapist_dashboard'))

# Справка и документация
@app.route('/help')
@login_required
def help_page():
    return render_template('help/help_center.html')

@app.route('/help/demo')
@login_required
def help_demo():
    return render_template('help/product_demo.html')

@app.route('/help/instructions')
@login_required
def help_instructions():
    return render_template('help/user_instructions.html')

# API маршруты
@app.route('/api/patient/<patient_id>/sessions')
@login_required
def patient_sessions_data(patient_id):
    try:
        current_user = get_current_user()
        if current_user.role != 'therapist' and current_user.user_id != patient_id:
            return jsonify({'error': 'Access denied'}), 403
        
        sessions = data_manager.therapy_manager.get_sessions_by_patient(patient_id)
        sessions_data = []
        for s in sessions:
            sessions_data.append({
                'date': s.date,
                'pre_sud': s.pre_sud,
                'post_sud': s.post_sud,
                'module_used': s.module_used,
                'duration': s.duration_minutes,
                'sud_reduction': s.post_sud - s.pre_sud
            })
        
        return jsonify(sessions_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Вспомогательные функции
def generate_recommendations(patient, preferences):
    recommendations = []
    
    if preferences.get('total_sessions', 0) >= 3:
        fav_module = preferences.get('favorite_module', '')
        
        if "Безопасное место" in fav_module:
            place = fav_module.split(" - ")[-1] if " - " in fav_module else "Море"
            recommendations.append({
                'type': 'interface_preset',
                'title': 'Быстрый доступ к безопасному месту',
                'description': f'Предлагать "{place}" первым в списке',
                'priority': 'high'
            })
    
    return recommendations

# Обработчики ошибок
@app.errorhandler(404)
def not_found_error(error):
    flash('Страница не найдена', 'error')
    return redirect(url_for('error/404.html'))

@app.errorhandler(500)
def internal_error(error):
    flash('Внутренняя ошибка сервера. Пожалуйста, попробуйте позже.', 'error')
    return redirect(url_for('error/500.html'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4040)