// Функция для отображения состояния загрузки
function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '<div class="loading">Загрузка данных...</div>';
    }
}

// Функция для отображения ошибки
function showError(containerId, error) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="error">Ошибка загрузки данных: ${error}</div>`;
    }
}

// Функция для обновления графиков
function updateCharts() {
    showLoading('sales-chart');
    showLoading('revenue-chart');
    
    fetch('/admin/orders/statistics-data/')
        .then(response => response.json())
        .then(data => {
            // Обновление графиков с новыми данными
            if (data.sales_chart) {
                document.getElementById('sales-chart').innerHTML = data.sales_chart;
            }
            if (data.revenue_chart) {
                document.getElementById('revenue-chart').innerHTML = data.revenue_chart;
            }
        })
        .catch(error => {
            showError('sales-chart', error);
            showError('revenue-chart', error);
        });
}

// Обновление каждые 5 минут
setInterval(updateCharts, 300000);
