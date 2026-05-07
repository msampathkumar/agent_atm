let trendChartInstance = null;
let appChartInstance = null;

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
        // 1. Fetch stats & charts data
        const metricsRes = await fetch('/api/metrics');
        const metrics = await metricsRes.json();

        document.getElementById('stat-total-events').innerText = metrics.stats.total_events.toLocaleString();
        document.getElementById('stat-total-requests').innerText = metrics.stats.total_requests.toLocaleString();
        document.getElementById('stat-total-responses').innerText = metrics.stats.total_responses.toLocaleString();
        document.getElementById('stat-total-tokens').innerText = metrics.stats.total_tokens.toLocaleString();

        // Dynamic color binding based on current active theme
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const textColor = currentTheme === 'light' ? '#4b5563' : '#9ca3af';
        const gridColor = currentTheme === 'light' ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.05)';

        // Render Trend Chart
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        if (trendChartInstance) trendChartInstance.destroy();
        
        trendChartInstance = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: metrics.daily_usage.map(d => d.day),
                datasets: [{
                    label: 'Tokens Consumed',
                    data: metrics.daily_usage.map(d => d.tokens),
                    borderColor: '#6366f1',
                    backgroundColor: currentTheme === 'light' ? 'rgba(79, 70, 229, 0.08)' : 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
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

        // 2. Fetch live events
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

// Initial load
loadData();
// Poll every 10 seconds for real-time update feel
setInterval(loadData, 10000);
