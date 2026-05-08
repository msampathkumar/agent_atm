let trendChartInstance = null;
let appChartInstance = null;
let currentWindow = "7d";
let refreshIntervalId = null;

const windowLabels = {
    "1m": "Last 1 Month",
    "7d": "Last 7 Days",
    "3d": "Last 3 Days",
    "1d": "Last 24 Hours",
    "12h": "Last 12 Hours",
    "6h": "Last 6 Hours",
    "4h": "Last 4 Hours",
    "2h": "Last 2 Hours",
    "1h": "Last 1 Hour",
    "30m": "Last 30 Minutes",
    "15m": "Last 15 Minutes",
    "5m": "Last 5 Minutes"
};

// Handle time window select change
function onWindowChange(val) {
    currentWindow = val;
    document.getElementById('chart-title-trend').innerText = `Token Consumption Trend (${windowLabels[val]})`;
    loadData();
}

// Start auto refresh polling
function startAutoRefresh() {
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    refreshIntervalId = setInterval(loadData, 10000);
}

// Stop auto refresh polling
function stopAutoRefresh() {
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        refreshIntervalId = null;
    }
}

// Toggle auto refresh on switch/checkbox check
function toggleAutoRefresh(enabled) {
    if (enabled) {
        startAutoRefresh();
    } else {
        stopAutoRefresh();
    }
}

// Theme Toggle Logic
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    
    const btn = document.getElementById('theme-toggle-btn');
    if (newTheme === 'light') {
        btn.innerHTML = '🌙 Dark Mode';
    } else {
        btn.innerHTML = '☀️ Light Mode';
    }
    
    // Trigger charts redrawing with updated colors
    if (trendChartInstance && appChartInstance) {
        const textColor = newTheme === 'light' ? '#4b5563' : '#9ca3af';
        const gridColor = newTheme === 'light' ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.05)';
        
        trendChartInstance.options.scales.y.ticks.color = textColor;
        trendChartInstance.options.scales.y.grid.color = gridColor;
        trendChartInstance.options.scales.x.ticks.color = textColor;
        
        appChartInstance.options.plugins.legend.labels.color = newTheme === 'light' ? '#111827' : '#f3f4f6';
        
        trendChartInstance.update();
        appChartInstance.update();
    }
}

async function loadData() {
    try {
        // 1. Fetch stats & charts data using selected time-window
        const metricsRes = await fetch(`/api/metrics?window=${currentWindow}`);
        const metrics = await metricsRes.json();

        document.getElementById('stat-total-events').innerText = metrics.stats.total_events.toLocaleString();
        document.getElementById('stat-total-requests').innerText = metrics.stats.total_requests.toLocaleString();
        document.getElementById('stat-total-responses').innerText = metrics.stats.total_responses.toLocaleString();
        document.getElementById('stat-request-tokens').innerText = metrics.stats.total_request_tokens.toLocaleString();
        document.getElementById('stat-response-tokens').innerText = metrics.stats.total_response_tokens.toLocaleString();
        document.getElementById('stat-total-tokens').innerText = metrics.stats.total_tokens.toLocaleString();

        // Dynamic color binding based on current active theme
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const textColor = currentTheme === 'light' ? '#4b5563' : '#9ca3af';
        const gridColor = currentTheme === 'light' ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.05)';

        // Render Trend Chart with Multiple Datasets (Total, Request, Response)
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        if (trendChartInstance) trendChartInstance.destroy();
        
        const chartLabels = metrics.chart_data.map(d => d.label);
        
        trendChartInstance = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: chartLabels,
                datasets: [
                    {
                        label: 'Total Tokens',
                        data: metrics.chart_data.map(d => d.total_tokens),
                        borderColor: '#ec4899',
                        backgroundColor: 'rgba(236, 72, 153, 0.05)',
                        fill: false,
                        tension: 0.3,
                        borderWidth: 3
                    },
                    {
                        label: 'Request Tokens',
                        data: metrics.chart_data.map(d => d.request_tokens),
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.05)',
                        fill: false,
                        tension: 0.3,
                        borderWidth: 2,
                        borderDash: [5, 5]
                    },
                    {
                        label: 'Response Tokens',
                        data: metrics.chart_data.map(d => d.response_tokens),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.05)',
                        fill: false,
                        tension: 0.3,
                        borderWidth: 2,
                        borderDash: [3, 3]
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: { color: currentTheme === 'light' ? '#111827' : '#f3f4f6', boxWidth: 15 }
                    }
                },
                scales: {
                    y: { grid: { color: gridColor }, ticks: { color: textColor } },
                    x: { grid: { display: false }, ticks: { color: textColor } }
                }
            }
        });

        // Render App Distribution Pie Chart
        const appCtx = document.getElementById('appChart').getContext('2d');
        if (appChartInstance) appChartInstance.destroy();
        
        const appLabels = Object.keys(metrics.by_app);
        const appData = Object.values(metrics.by_app);

        appChartInstance = new Chart(appCtx, {
            type: 'doughnut',
            data: {
                labels: appLabels,
                datasets: [{
                    data: appData,
                    backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: currentTheme === 'light' ? '#111827' : '#f3f4f6', boxWidth: 12 } }
                }
            }
        });

        // 2. Fetch live events (Limit remains 100)
        const eventsRes = await fetch('/api/events');
        const events = await eventsRes.json();

        const tbody = document.getElementById('events-tbody');
        tbody.innerHTML = '';
        
        if (events.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">No events recorded yet.</td></tr>';
            return;
        }

        events.forEach(ev => {
            const tr = document.createElement('tr');
            const timeStr = new Date(ev.timestamp).toLocaleTimeString();
            const typeBadge = `<span class="badge ${ev.event_type}">${ev.event_type}</span>`;
            
            // Build inline metadata badges
            let metaHtml = '';
            if (ev.tags && ev.tags.length > 0) {
                ev.tags.forEach(tag => {
                    metaHtml += `<span class="tag-badge">${tag}</span>`;
                });
            }
            if (ev.config) {
                Object.entries(ev.config).forEach(([k, v]) => {
                    metaHtml += `<span class="config-badge">${k}=${v}</span>`;
                });
            }
            if (!metaHtml) {
                metaHtml = '<span style="color: var(--text-secondary); font-size: 0.8rem;">None</span>';
            }
            
            tr.innerHTML = `
                <td>${timeStr}</td>
                <td>${typeBadge}</td>
                <td style="font-weight: 600;">${ev.token_count.toLocaleString()}</td>
                <td>${ev.model_id}</td>
                <td>${ev.app_id}</td>
                <td>${ev.username}</td>
                <td><code>${ev.session_id}</code></td>
                <td>${metaHtml}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        console.error("Error loading telemetry data:", err);
    }
}

// Initial load setup
document.getElementById('chart-title-trend').innerText = `Token Consumption Trend (${windowLabels[currentWindow]})`;
loadData();

// Start auto-refresh dynamically based on initial checkbox state
if (document.getElementById('auto-refresh-checkbox').checked) {
    startAutoRefresh();
}
