from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from config import Config
from models.data_manager import DataManager
from auth.auth import login_required, therapist_required, patient_required
from auth.utils import get_current_user, is_therapist, is_patient, is_superadmin
import json
from datetime import datetime
import random

app = Flask(__name__)
app.config.from_object(Config)
data_manager = DataManager()

@app.context_processor
def utility_processor():
    def now():
        return datetime.now()
    return dict(now=now)

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
    # Очищаем flash сообщения при загрузке страницы
    session.pop('_flashes', None)
    
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

# Управление пациентами
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

@app.route('/therapist/session/<patient_id>')
@therapist_required
def therapist_session(patient_id):
    """Страница управления VR-сессией"""
    if not session.get('is_licensed'):
        flash('Для проведения сессий необходимо пройти обучение и получить лицензию', 'warning')
        return redirect(url_for('therapist_training'))
    
    patient = data_manager.user_manager.get_user_by_id(patient_id)
    if not patient or patient.therapist_id != session['user_id']:
        flash('Пациент не найден или доступ запрещен', 'error')
        return redirect(url_for('therapist_dashboard'))
    
    return render_template('session/session_control.html', patient=patient)

# Добавляем в существующий app.py новые эндпоинты

@app.route('/api/session/vital_signs/<patient_id>')
@therapist_required
def get_vital_signs(patient_id):
    """Получение текущих показателей жизнедеятельности"""
    try:
        # Симуляция реальных данных с датчиков
        import random
        import time
        
        # Базовые значения в зависимости от фазы сессии
        sim_data = session.get('current_simulation', {})
        current_phase = sim_data.get('current_phase', 'pre')
        base_sud = sim_data.get('current_sud', 5)
        
        # Генерируем реалистичные данные на основе SUD
        base_hr = 70 + (base_sud * 3)  # пульс увеличивается с SUD
        hr_variation = random.randint(-5, 5)
        
        base_sys = 120 + (base_sud * 2)  # систолическое давление
        base_dia = 80 + (base_sud * 1)   # диастолическое давление
        
        vital_signs = {
            'heart_rate': max(60, base_hr + hr_variation),
            'blood_pressure': f"{base_sys}/{base_dia}",
            'temperature': round(36.6 + random.uniform(-0.2, 0.2), 1),
            'stress_level': base_sud,
            'respiration_rate': 16 + base_sud,
            'skin_conductance': round(2 + (base_sud * 0.3), 1),
            'oxygen_saturation': 98 - (base_sud * 0.5),
            'timestamp': int(time.time() * 1000)
        }
        
        return jsonify({
            'success': True,
            'vital_signs': vital_signs
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/submit_sud', methods=['POST'])
@therapist_required
def submit_sud():
    """Обработка оценки SUD от пациента"""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        sud_value = data.get('sud_value')
        phase = data.get('phase')
        
        # Обновляем данные симуляции
        sim_data = session.get('current_simulation', {})
        sim_data['current_sud'] = sud_value
        sim_data['current_phase'] = phase
        session['current_simulation'] = sim_data
        
        # Генерируем реакцию пациента на основе SUD
        reactions = {
            'pre': [
                f"Оцениваю начальное состояние как {sud_value}",
                f"Чувствую напряжение на уровне {sud_value}",
                f"Моя начальная тревога: {sud_value}"
            ],
            'during': [
                f"Сейчас чувствую {sud_value}",
                f"Текущий уровень дистресса: {sud_value}",
                f"Оцениваю как {sud_value}"
            ],
            'post': [
                f"Финальная оценка: {sud_value}",
                f"Завершаю с уровнем {sud_value}",
                f"Итоговый SUD: {sud_value}"
            ]
        }
        
        reaction = random.choice(reactions.get(phase, ['Оцениваю состояние...']))
        
        return jsonify({
            'success': True,
            'sud_value': sud_value,
            'phase': phase,
            'patient_reaction': reaction,
            'message': f'SUD оценка сохранена: {sud_value}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/start', methods=['POST'])
@therapist_required
def start_session():
    """Запуск VR-сессии"""
    data = request.get_json()
    patient_id = data.get('patient_id')
    environment = data.get('environment', 'safe_place')
    
    # Здесь будет логика запуска реальной VR-сессии
    # Пока просто симуляция
    session['current_session'] = {
        'patient_id': patient_id,
        'environment': environment,
        'started_at': datetime.now().isoformat(),
        'status': 'active'
    }
    
    return jsonify({
        'success': True,
        'message': f'Сессия запущена в среде: {environment}',
        'session_id': f"VR_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    })

@app.route('/api/session/stop', methods=['POST'])
@therapist_required
def stop_session():
    """Экстренная остановка сессии"""
    session_data = session.get('current_session')
    if session_data:
        # Записываем данные сессии
        session_id = f"VR_{session_data['patient_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Очищаем текущую сессию
        session.pop('current_session', None)
        
        return jsonify({
            'success': True,
            'message': 'Сессия экстренно остановлена',
            'session_id': session_id
        })
    
    return jsonify({'success': False, 'message': 'Активная сессия не найдена'})

@app.route('/api/session/update_sud', methods=['POST'])
@therapist_required
def update_sud():
    """Обновление SUD пациента"""
    data = request.get_json()
    patient_id = data.get('patient_id')
    sud_value = data.get('sud_value')
    phase = data.get('phase', 'during')  # pre, during, post
    
    # Здесь будет логика сохранения SUD в базе данных
    return jsonify({
        'success': True,
        'message': f'SUD обновлен: {sud_value} (фаза: {phase})',
        'sud_value': sud_value
    })

@app.route('/api/session/vital_signs', methods=['POST'])
@therapist_required
def update_vital_signs():
    """Обновление показателей жизнедеятельности"""
    data = request.get_json()
    patient_id = data.get('patient_id')
    
    # Симуляция данных с датчиков
    import random
    vital_signs = {
        'heart_rate': random.randint(60, 120),
        'blood_pressure': f"{random.randint(110, 140)}/{random.randint(70, 90)}",
        'temperature': round(random.uniform(36.2, 37.2), 1),
        'stress_level': random.randint(1, 10)
    }
    
    return jsonify({
        'success': True,
        'vital_signs': vital_signs
    })

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

# Новые API для симуляции сценариев
@app.route('/api/session/scenarios')
@therapist_required
def get_session_scenarios():
    """Возвращает доступные сценарии для симуляции"""
    scenarios = [
        {
            'id': 'scenario_1',
            'name': 'Пациент с фобией высоты',
            'description': 'Пациент испытывает страх высоты в городской среде',
            'initial_sud': 8,
            'expected_progress': [6, 4, 2],
            'environment': 'exposure_city',
            'patient_profile': 'Мужчина, 35 лет, страх высоты после падения с лестницы'
        },
        {
            'id': 'scenario_2',
            'name': 'Пациент с ПТСР после ДТП',
            'description': 'Пациент переживает последствия автомобильной аварии',
            'initial_sud': 9,
            'expected_progress': [7, 5, 3],
            'environment': 'exposure_city',
            'patient_profile': 'Женщина, 28 лет, ПТСР после серьезного ДТП'
        },
        {
            'id': 'scenario_3',
            'name': 'Пациент с социальной тревожностью',
            'description': 'Страх публичных выступлений и социальных ситуаций',
            'initial_sud': 7,
            'expected_progress': [5, 3, 2],
            'environment': 'exposure_city',
            'patient_profile': 'Мужчина, 22 года, студент, страх публичных выступлений'
        },
        {
            'id': 'scenario_4', 
            'name': 'Пациент с тревогой в закрытых пространствах',
            'description': 'Клаустрофобия в лифтах и небольших помещениях',
            'initial_sud': 8,
            'expected_progress': [6, 4, 2],
            'environment': 'exposure_city',
            'patient_profile': 'Женщина, 45 лет, клаустрофобия после застревания в лифте'
        },
        {
            'id': 'scenario_5',
            'name': 'Пациент с тревогой в метро',
            'description': 'Панические атаки в метро и общественном транспорте',
            'initial_sud': 9,
            'expected_progress': [7, 5, 3],
            'environment': 'exposure_city', 
            'patient_profile': 'Мужчина, 31 год, панические атаки в метро после теракта'
        }
    ]
    return jsonify(scenarios)

@app.route('/api/session/start_scenario', methods=['POST'])
@therapist_required
def start_scenario():
    """Запуск симуляции по выбранному сценарию"""
    data = request.get_json()
    scenario_id = data.get('scenario_id')
    patient_id = data.get('patient_id')
    
    # Находим выбранный сценарий
    scenarios = get_session_scenarios().get_json()
    selected_scenario = next((s for s in scenarios if s['id'] == scenario_id), None)
    
    if not selected_scenario:
        return jsonify({'success': False, 'error': 'Сценарий не найден'})
    
    # Создаем сессию симуляции
    session_id = f"SIM_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    session['current_simulation'] = {
        'session_id': session_id,
        'patient_id': patient_id,
        'scenario': selected_scenario,
        'current_phase': 'pre',
        'current_sud': selected_scenario['initial_sud'],
        'started_at': datetime.now().isoformat(),
        'status': 'active'
    }
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'scenario': selected_scenario,
        'message': f'Симуляция запущена: {selected_scenario["name"]}'
    })

@app.route('/api/session/simulation/progress', methods=['POST'])
@therapist_required
def simulation_progress():
    """Прогресс симуляции - переход между фазами"""
    data = request.get_json()
    phase = data.get('phase')  # pre, during_1, during_2, post
    
    sim_data = session.get('current_simulation')
    if not sim_data:
        return jsonify({'success': False, 'error': 'Активная симуляция не найдена'})
    
    scenario = sim_data['scenario']
    
    # Определяем SUD для текущей фазы
    phase_sud_map = {
        'pre': scenario['initial_sud'],
        'during_1': scenario['expected_progress'][0],
        'during_2': scenario['expected_progress'][1], 
        'post': scenario['expected_progress'][2]
    }
    
    new_sud = phase_sud_map.get(phase, scenario['initial_sud'])
    
    # Обновляем данные симуляции
    session['current_simulation']['current_phase'] = phase
    session['current_simulation']['current_sud'] = new_sud
    
    # Генерируем реалистичные показатели жизнедеятельности на основе SUD
    vital_signs = generate_realistic_vital_signs(new_sud)
    
    return jsonify({
        'success': True,
        'phase': phase,
        'sud_value': new_sud,
        'vital_signs': vital_signs,
        'patient_reaction': generate_patient_reaction(phase, new_sud, scenario['name'])
    })

def generate_realistic_vital_signs(sud_value):
    """Генерирует реалистичные показатели на основе уровня SUD"""
    base_hr = 70  # базовый пульс
    hr_variation = sud_value * 3  # пульс увеличивается с ростом SUD
    
    base_sys = 120  # базовое систолическое
    sys_variation = sud_value * 2
    
    base_dia = 80   # базовое диастолическое  
    dia_variation = sud_value * 1
    
    return {
        'heart_rate': base_hr + random.randint(hr_variation - 5, hr_variation + 5),
        'blood_pressure': f"{base_sys + sys_variation}/{base_dia + dia_variation}",
        'temperature': round(36.6 + random.uniform(-0.2, 0.2), 1),
        'stress_level': sud_value,
        'respiration_rate': 16 + sud_value,  # частота дыхания
        'skin_conductance': 2 + (sud_value * 0.5)  # кожно-гальваническая реакция
    }

def generate_patient_reaction(phase, sud_value, scenario_name):
    """Генерирует реалистичные реакции пациента"""
    reactions = {
        'pre': [
            "Чувствую небольшое напряжение перед началом",
            "Немного тревожно, но готов начать",
            "Дышу глубже, пытаюсь успокоиться",
            "Напряжение в плечах, но справляюсь"
        ],
        'during_1': [
            "Чувствую усиление тревоги",
            "Сердце бьется чаще, но продолжаю",
            "Пытаюсь использовать дыхательные техники", 
            "Напоминаю себе, что это безопасно"
        ],
        'during_2': [
            "Тревога постепенно снижается",
            "Чувствую больше контроля над ситуацией",
            "Дыхание становится ровнее",
            "Мышечное напряжение уменьшается"
        ],
        'post': [
            "Чувствую облегчение и усталость",
            "Горжусь тем, что справился с ситуацией",
            "Тревога значительно уменьшилась",
            "Чувствую прогресс в терапии"
        ]
    }
    
    # Добавляем специфичные реакции для сценариев
    scenario_reactions = {
        'Пациент с фобией высоты': {
            'during_1': ["Высота пугает, но вид красивый", "Ноги немного дрожат", "Стараюсь не смотреть вниз"],
            'during_2': ["Постепенно привыкаю к высоте", "Могу смотреть вокруг более спокойно"]
        },
        'Пациент с ПТСР после ДТП': {
            'during_1': ["Воспоминания о аварии", "Тело напрягается при виде машин", "Стараюсь дышать глубже"],
            'during_2': ["Понимаю, что сейчас все безопасно", "Тревога отступает"]
        }
    }
    
    phase_reactions = reactions.get(phase, [])
    
    # Добавляем специфичные реакции если есть
    if scenario_name in scenario_reactions and phase in scenario_reactions[scenario_name]:
        phase_reactions.extend(scenario_reactions[scenario_name][phase])
    
    return random.choice(phase_reactions)

@app.route('/api/session/simulation/stop', methods=['POST'])
@therapist_required  
def stop_simulation():
    """Остановка симуляции"""
    sim_data = session.get('current_simulation')
    if sim_data:
        session.pop('current_simulation', None)
        return jsonify({
            'success': True,
            'message': 'Симуляция завершена',
            'session_data': sim_data
        })
    
    return jsonify({'success': False, 'message': 'Активная симуляция не найдена'})

# Обработчики ошибок
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4040)