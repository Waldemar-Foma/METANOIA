// Основной JavaScript файл
class ChartManager {
    constructor() {
        this.charts = new Map();
    }

    createSUDChart(canvasId, sessionsData) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        const dates = sessionsData.map(s => new Date(s.date).toLocaleDateString());
        const preSUD = sessionsData.map(s => s.pre_sud);
        const postSUD = sessionsData.map(s => s.post_sud);

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Pre-SUD',
                        data: preSUD,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#ef4444',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    },
                    {
                        label: 'Post-SUD',
                        data: postSUD,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Динамика SUD по сессиям',
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        color: '#1e293b'
                    },
                    legend: {
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 10,
                        title: {
                            display: true,
                            text: 'Уровень SUD',
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });

        this.charts.set(canvasId, chart);
        return chart;
    }

    createModuleUsageChart(canvasId, preferences) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        const moduleCounts = preferences.module_counts || {};
        
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(moduleCounts),
                datasets: [{
                    data: Object.values(moduleCounts),
                    backgroundColor: [
                        '#2563eb',
                        '#10b981', 
                        '#f59e0b',
                        '#8b5cf6',
                        '#06b6d4',
                        '#ec4899'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    title: {
                        display: true,
                        text: 'Использование модулей терапии',
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        color: '#1e293b'
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            font: {
                                size: 11,
                                weight: '600'
                            }
                        }
                    }
                },
                animation: {
                    animateScale: true,
                    animateRotate: true
                }
            }
        });

        this.charts.set(canvasId, chart);
        return chart;
    }

    createProgressChart(canvasId, sessionsData) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        const dates = sessionsData.map(s => new Date(s.date).toLocaleDateString());
        const reduction = sessionsData.map(s => s.sud_reduction);

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Снижение SUD',
                    data: reduction,
                    backgroundColor: reduction.map(val => 
                        val < -2 ? '#10b981' : val < 0 ? '#f59e0b' : '#ef4444'
                    ),
                    borderWidth: 0,
                    borderRadius: 8,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Эффективность сессий (снижение SUD)',
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        color: '#1e293b'
                    }
                },
                scales: {
                    y: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });

        this.charts.set(canvasId, chart);
        return chart;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    window.chartManager = new ChartManager();
    
    // Улучшенная анимация появления элементов
    const animateOnScroll = () => {
        const elements = document.querySelectorAll('.card, .btn, .stat-card');
        elements.forEach((el, index) => {
            const position = el.getBoundingClientRect();
            if (position.top < window.innerHeight - 50) {
                setTimeout(() => {
                    el.style.opacity = '1';
                    el.style.transform = 'translateY(0)';
                }, index * 100);
            }
        });
    };
    
    // Инициализация стилей для анимации
    document.querySelectorAll('.card, .btn, .stat-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    });
    
    window.addEventListener('scroll', animateOnScroll);
    animateOnScroll(); // Запустить сразу для видимых элементов
    
    // Добавляем интерактивность для карточек
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(-8px)';
        });
    });
});