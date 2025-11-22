// JavaScript для страниц аутентификации
document.addEventListener('DOMContentLoaded', function() {
    // Валидация формы входа
    const loginForm = document.querySelector('.auth-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const username = document.getElementById('username');
            const password = document.getElementById('password');
            
            if (!username.value.trim() || !password.value.trim()) {
                e.preventDefault();
                showError('Пожалуйста, заполните все поля');
                return;
            }
            
            // Показываем состояние загрузки
            const submitBtn = this.querySelector('.auth-btn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вход...';
            }
        });
    }
    
    // Показать/скрыть пароль
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.innerHTML = '<i class="fas fa-eye"></i>';
        toggle.className = 'password-toggle';
        
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(toggle);
        
        toggle.addEventListener('click', function() {
            if (input.type === 'password') {
                input.type = 'text';
                toggle.innerHTML = '<i class="fas fa-eye-slash"></i>';
                toggle.style.color = 'var(--primary)';
            } else {
                input.type = 'password';
                toggle.innerHTML = '<i class="fas fa-eye"></i>';
                toggle.style.color = 'var(--text-muted)';
            }
        });
    });
    
    // Добавляем анимацию при фокусе на инпуты
    const formInputs = document.querySelectorAll('.form-input');
    formInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });
    
    // Функция показа ошибок
    function showError(message) {
        // Создаем временное уведомление об ошибке
        const errorDiv = document.createElement('div');
        errorDiv.className = 'flash-message flash-error';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            <span>${message}</span>
        `;
        
        errorDiv.style.position = 'fixed';
        errorDiv.style.top = '20px';
        errorDiv.style.right = '20px';
        errorDiv.style.zIndex = '10000';
        errorDiv.style.animation = 'slideInRight 0.3s ease-out';
        
        document.body.appendChild(errorDiv);
        
        // Удаляем через 5 секунд
        setTimeout(() => {
            errorDiv.style.animation = 'slideOutRight 0.3s ease-in forwards';
            setTimeout(() => errorDiv.remove(), 300);
        }, 5000);
    }
    
    // Добавляем интерактивность для карточек фич
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(-8px)';
        });
    });
    
    // Анимация для списка возможностей терапевтов
    const featureItems = document.querySelectorAll('.features-list li');
    featureItems.forEach((item, index) => {
        item.style.animationDelay = `${index * 0.1}s`;
        item.style.animation = 'slideInUp 0.5s ease-out forwards';
        item.style.opacity = '0';
    });
});