/**
 * Dashboard JavaScript
 * Auto-refresco cada 30 segundos usando fetch a los endpoints del API.
 */

// Instancias de los gráficos
let commandsChart = null;
let apisChart = null;
let timelineChart = null;

// Colores para los gráficos
const COLORS = [
    '#00d4ff', '#00ff88', '#ff6b6b', '#ffd93d',
    '#c56cf0', '#ff9f43', '#0abde3', '#ee5a24'
];

/**
 * Inicializa todos los gráficos de Chart.js.
 */
function initCharts() {
    // Opciones comunes
    const commonOptions = {
        responsive: true,
        plugins: {
            legend: {
                labels: { color: '#e0e0e0' }
            }
        },
        scales: {
            x: {
                ticks: { color: '#888' },
                grid: { color: '#2a2a5e' }
            },
            y: {
                ticks: { color: '#888' },
                grid: { color: '#2a2a5e' },
                beginAtZero: true
            }
        }
    };

    // Gráfico de comandos
    const cmdCtx = document.getElementById('commandsChart').getContext('2d');
    commandsChart = new Chart(cmdCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Peticiones',
                data: [],
                backgroundColor: COLORS,
                borderColor: COLORS.map(c => c + '80'),
                borderWidth: 1
            }]
        },
        options: {
            ...commonOptions,
            plugins: {
                ...commonOptions.plugins,
                legend: { display: false }
            }
        }
    });

    // Gráfico de APIs
    const apiCtx = document.getElementById('apisChart').getContext('2d');
    apisChart = new Chart(apiCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Peticiones',
                data: [],
                backgroundColor: COLORS,
                borderColor: COLORS.map(c => c + '80'),
                borderWidth: 1
            }]
        },
        options: {
            ...commonOptions,
            plugins: {
                ...commonOptions.plugins,
                legend: { display: false }
            }
        }
    });

    // Gráfico de timeline
    const tlCtx = document.getElementById('timelineChart').getContext('2d');
    timelineChart = new Chart(tlCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Actividad',
                data: [],
                borderColor: '#00d4ff',
                backgroundColor: 'rgba(0, 212, 255, 0.1)',
                fill: true,
                tension: 0.3,
                pointBackgroundColor: '#00d4ff',
                pointBorderColor: '#00d4ff'
            }]
        },
        options: commonOptions
    });
}

/**
 * Actualiza las tarjetas de resumen.
 */
async function updateCards() {
    try {
        const response = await fetch('/api/stats/general');
        const data = await response.json();

        document.getElementById('total-users').textContent = data.total_users || 0;
        document.getElementById('active-users').textContent = data.active_users_today || 0;
        document.getElementById('total-commands').textContent = data.total_commands_today || 0;
        document.getElementById('total-api-calls').textContent = data.total_api_calls_today || 0;
    } catch (error) {
        console.error('Error actualizando tarjetas:', error);
    }
}

/**
 * Actualiza el gráfico de comandos.
 */
async function updateCommandsChart() {
    try {
        const response = await fetch('/api/stats/commands');
        const data = await response.json();

        const labels = Object.keys(data);
        const values = Object.values(data);

        commandsChart.data.labels = labels;
        commandsChart.data.datasets[0].data = values;
        commandsChart.update();
    } catch (error) {
        console.error('Error actualizando gráfico de comandos:', error);
    }
}

/**
 * Actualiza el gráfico de APIs.
 */
async function updateApisChart() {
    try {
        const response = await fetch('/api/stats/apis');
        const data = await response.json();

        const labels = Object.keys(data);
        const values = Object.values(data);

        apisChart.data.labels = labels;
        apisChart.data.datasets[0].data = values;
        apisChart.update();
    } catch (error) {
        console.error('Error actualizando gráfico de APIs:', error);
    }
}

/**
 * Actualiza el gráfico de timeline.
 */
async function updateTimelineChart() {
    try {
        const response = await fetch('/api/stats/timeline');
        const data = await response.json();

        const labels = data.map(item => item.hour + ':00');
        const values = data.map(item => item.count);

        timelineChart.data.labels = labels;
        timelineChart.data.datasets[0].data = values;
        timelineChart.update();
    } catch (error) {
        console.error('Error actualizando timeline:', error);
    }
}

/**
 * Actualiza la tabla de peticiones recientes.
 */
async function updateRecentTable() {
    try {
        const response = await fetch('/api/stats/recent');
        const data = await response.json();

        const tbody = document.getElementById('recent-table');

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#666;">Sin peticiones todavía</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(item => {
            const statusClass = item.success ? 'status-success' : 'status-fail';
            const statusText = item.success ? '✅ Éxito' : '❌ Fallo';
            const responseTime = item.response_time_ms ? item.response_time_ms.toFixed(0) : 'N/A';
            const timestamp = new Date(item.timestamp).toLocaleString('es-ES');

            return `<tr>
                <td>${timestamp}</td>
                <td>${item.user_id}</td>
                <td>${item.command}</td>
                <td>${responseTime}</td>
                <td class="${statusClass}">${statusText}</td>
            </tr>`;
        }).join('');
    } catch (error) {
        console.error('Error actualizando tabla reciente:', error);
    }
}

/**
 * Actualiza todos los componentes del dashboard.
 */
async function updateAll() {
    await Promise.all([
        updateCards(),
        updateCommandsChart(),
        updateApisChart(),
        updateTimelineChart(),
        updateRecentTable()
    ]);

    document.getElementById('last-update').textContent = new Date().toLocaleString('es-ES');
}

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    updateAll();

    // Auto-refresco cada 30 segundos
    setInterval(updateAll, 30000);
});
