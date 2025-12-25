/**
 * SentinelWatch SIEM Dashboard - Frontend JavaScript
 * SOC-style dashboard with real-time updates and Chart.js visualizations
 */

const API_BASE = window.location.origin;
let severityChart = null;
let activityChart = null;
let refreshInterval = null;

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    loadDashboard();
    startAutoRefresh();
});

/**
 * Initialize Chart.js charts for visualizations
 */
function initializeCharts() {
    // Severity Distribution Chart
    const severityCtx = document.getElementById('severityChart').getContext('2d');
    severityChart = new Chart(severityCtx, {
        type: 'doughnut',
        data: {
            labels: ['Critical', 'High', 'Medium', 'Low'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(220, 38, 38, 0.8)',  // Red for Critical
                    'rgba(249, 115, 22, 0.8)', // Orange for High
                    'rgba(234, 179, 8, 0.8)',  // Yellow for Medium
                    'rgba(59, 130, 246, 0.8)'  // Blue for Low
                ],
                borderColor: [
                    'rgba(220, 38, 38, 1)',
                    'rgba(249, 115, 22, 1)',
                    'rgba(234, 179, 8, 1)',
                    'rgba(59, 130, 246, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e5e7eb'
                    }
                }
            }
        }
    });

    // Activity Over Time Chart
    const activityCtx = document.getElementById('activityChart').getContext('2d');
    activityChart = new Chart(activityCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Alerts',
                data: [],
                borderColor: 'rgba(239, 68, 68, 1)',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#9ca3af',
                        stepSize: 1
                    },
                    grid: {
                        color: 'rgba(75, 85, 99, 0.3)'
                    }
                },
                x: {
                    ticks: {
                        color: '#9ca3af'
                    },
                    grid: {
                        color: 'rgba(75, 85, 99, 0.3)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#e5e7eb'
                    }
                }
            }
        }
    });
}

/**
 * Load dashboard data from API
 */
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/dashboard/stats`);
        const data = await response.json();
        
        // Update statistics cards
        document.getElementById('total-logs').textContent = data.total_logs.toLocaleString();
        document.getElementById('critical-alerts').textContent = data.alerts_by_severity.Critical || 0;
        document.getElementById('high-alerts').textContent = data.alerts_by_severity.High || 0;
        document.getElementById('total-alerts').textContent = data.total_alerts.toLocaleString();
        
        // Update severity chart
        severityChart.data.datasets[0].data = [
            data.alerts_by_severity.Critical || 0,
            data.alerts_by_severity.High || 0,
            data.alerts_by_severity.Medium || 0,
            data.alerts_by_severity.Low || 0
        ];
        severityChart.update();
        
        // Update activity chart (last 10 alerts timeline)
        updateActivityChart(data.recent_alerts);
        
        // Update alerts table
        updateAlertsTable(data.recent_alerts);
        
        // Update last update timestamp
        document.getElementById('last-update').textContent = 
            `Last updated: ${new Date().toLocaleTimeString()}`;
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('Failed to load dashboard data. Please refresh.');
    }
}

/**
 * Update activity chart with recent alerts
 */
function updateActivityChart(alerts) {
    // Group alerts by hour for the last 24 hours
    const now = new Date();
    const hours = [];
    const counts = [];
    
    for (let i = 23; i >= 0; i--) {
        const hour = new Date(now);
        hour.setHours(hour.getHours() - i);
        hours.push(hour.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
        counts.push(0);
    }
    
    // Count alerts per hour
    alerts.forEach(alert => {
        const alertTime = new Date(alert.triggered_at);
        const hoursAgo = Math.floor((now - alertTime) / (1000 * 60 * 60));
        if (hoursAgo >= 0 && hoursAgo < 24) {
            counts[23 - hoursAgo]++;
        }
    });
    
    activityChart.data.labels = hours;
    activityChart.data.datasets[0].data = counts;
    activityChart.update();
}

/**
 * Update alerts table with recent alerts
 */
function updateAlertsTable(alerts) {
    const tbody = document.getElementById('alerts-table-body');
    const noAlerts = document.getElementById('no-alerts');
    
    if (alerts.length === 0) {
        tbody.innerHTML = '';
        noAlerts.classList.remove('hidden');
        return;
    }
    
    noAlerts.classList.add('hidden');
    tbody.innerHTML = alerts.map(alert => {
        const severityClass = `severity-${alert.severity.toLowerCase()}`;
        const time = new Date(alert.triggered_at).toLocaleString();
        
        return `
            <tr class="hover:bg-gray-700">
                <td class="px-4 py-3 text-sm">${time}</td>
                <td class="px-4 py-3">
                    <span class="px-2 py-1 rounded text-xs font-semibold ${severityClass}">
                        ${alert.severity}
                    </span>
                </td>
                <td class="px-4 py-3 text-sm">${alert.rule_name}</td>
                <td class="px-4 py-3 text-sm font-mono">${alert.source_ip || 'N/A'}</td>
                <td class="px-4 py-3 text-sm">${alert.username || 'N/A'}</td>
                <td class="px-4 py-3 text-sm">
                    <div class="cursor-pointer hover:text-blue-400" onclick="showAlertDetails('${alert.alert_id}')">
                        ${alert.description.substring(0, 60)}${alert.description.length > 60 ? '...' : ''}
                    </div>
                </td>
                <td class="px-4 py-3">
                    <button onclick="showAlertDetails('${alert.alert_id}')" 
                            class="bg-gray-600 hover:bg-gray-700 px-2 py-1 rounded text-xs mr-2">
                        View
                    </button>
                    ${!alert.acknowledged ? `<button onclick="acknowledgeAlert('${alert.alert_id}')" 
                            class="bg-blue-600 hover:bg-blue-700 px-2 py-1 rounded text-xs mr-2">
                        Ack
                    </button>` : ''}
                    ${!alert.resolved ? `<button onclick="resolveAlert('${alert.alert_id}')" 
                            class="bg-green-600 hover:bg-green-700 px-2 py-1 rounded text-xs">
                        Resolve
                    </button>` : '<span class="text-green-400 text-xs">Resolved</span>'}
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Apply filters to alerts table
 */
async function applyFilters() {
    const severity = document.getElementById('severity-filter').value;
    const ruleName = document.getElementById('rule-filter').value;
    
    try {
        let url = `${API_BASE}/api/alerts?limit=50`;
        if (severity) url += `&severity=${severity}`;
        if (ruleName) url += `&rule_name=${ruleName}`;
        
        const response = await fetch(url);
        const data = await response.json();
        updateAlertsTable(data.alerts);
    } catch (error) {
        console.error('Error filtering alerts:', error);
    }
}

/**
 * Acknowledge an alert
 */
async function acknowledgeAlert(alertId) {
    try {
        const response = await fetch(`${API_BASE}/api/alerts/${alertId}/acknowledge`, {
            method: 'POST'
        });
        
        if (response.ok) {
            loadDashboard();
        } else {
            showError('Failed to acknowledge alert');
        }
    } catch (error) {
        console.error('Error acknowledging alert:', error);
        showError('Failed to acknowledge alert');
    }
}

/**
 * Resolve an alert
 */
async function resolveAlert(alertId) {
    try {
        const response = await fetch(`${API_BASE}/api/alerts/${alertId}/resolve`, {
            method: 'POST'
        });
        
        if (response.ok) {
            loadDashboard();
        } else {
            showError('Failed to resolve alert');
        }
    } catch (error) {
        console.error('Error resolving alert:', error);
        showError('Failed to resolve alert');
    }
}

/**
 * Upload log file
 */
async function uploadLogFile() {
    const fileInput = document.getElementById('log-file-input');
    const statusSpan = document.getElementById('upload-status');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showError('Please select a log file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    statusSpan.textContent = 'Uploading...';
    statusSpan.className = 'text-sm text-yellow-400';
    
    try {
        const response = await fetch(`${API_BASE}/api/logs/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusSpan.textContent = `Success! Ingested ${data.data.ingested} logs, generated ${data.data.alerts_generated} alerts`;
            statusSpan.className = 'text-sm text-green-400';
            fileInput.value = '';
            
            // Refresh dashboard after short delay
            setTimeout(() => {
                loadDashboard();
                statusSpan.textContent = '';
            }, 2000);
        } else {
            throw new Error(data.detail || 'Upload failed');
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        statusSpan.textContent = `Error: ${error.message}`;
        statusSpan.className = 'text-sm text-red-400';
    }
}

/**
 * Refresh dashboard manually
 */
function refreshDashboard() {
    loadDashboard();
}

/**
 * Start auto-refresh interval (every 30 seconds)
 */
function startAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    refreshInterval = setInterval(loadDashboard, 30000); // 30 seconds
}

/**
 * Show error message
 */
function showError(message) {
    // Simple error display - could be enhanced with toast notifications
    alert(message);
}

/**
 * Show alert details modal
 */
async function showAlertDetails(alertId) {
    try {
        const response = await fetch(`${API_BASE}/api/alerts/${alertId}`);
        const alert = await response.json();
        
        const modal = document.getElementById('alert-modal');
        const content = document.getElementById('alert-details-content');
        
        const severityClass = `severity-${alert.severity.toLowerCase()}`;
        
        content.innerHTML = `
            <div class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="text-gray-400 text-sm">Severity</label>
                        <div class="mt-1">
                            <span class="px-3 py-1 rounded text-sm font-semibold ${severityClass}">
                                ${alert.severity}
                            </span>
                        </div>
                    </div>
                    <div>
                        <label class="text-gray-400 text-sm">Rule Name</label>
                        <div class="mt-1 text-white">${alert.rule_name}</div>
                    </div>
                    <div>
                        <label class="text-gray-400 text-sm">Source IP</label>
                        <div class="mt-1 text-white font-mono">${alert.source_ip || 'N/A'}</div>
                    </div>
                    <div>
                        <label class="text-gray-400 text-sm">Username</label>
                        <div class="mt-1 text-white">${alert.username || 'N/A'}</div>
                    </div>
                    <div>
                        <label class="text-gray-400 text-sm">Triggered At</label>
                        <div class="mt-1 text-white">${new Date(alert.triggered_at).toLocaleString()}</div>
                    </div>
                    <div>
                        <label class="text-gray-400 text-sm">Status</label>
                        <div class="mt-1">
                            ${alert.resolved ? '<span class="text-green-400">Resolved</span>' : 
                              alert.acknowledged ? '<span class="text-yellow-400">Acknowledged</span>' : 
                              '<span class="text-red-400">New</span>'}
                        </div>
                    </div>
                </div>
                
                <div>
                    <label class="text-gray-400 text-sm">Description</label>
                    <div class="mt-1 text-white bg-gray-700 p-3 rounded">${alert.description}</div>
                </div>
                
                ${alert.context ? `
                <div>
                    <label class="text-gray-400 text-sm">Context</label>
                    <div class="mt-1 text-white bg-gray-700 p-3 rounded">
                        <pre class="text-xs overflow-auto">${JSON.stringify(alert.context, null, 2)}</pre>
                    </div>
                </div>
                ` : ''}
                
                ${alert.notes ? `
                <div>
                    <label class="text-gray-400 text-sm">Notes</label>
                    <div class="mt-1 text-white bg-gray-700 p-3 rounded">${alert.notes}</div>
                </div>
                ` : ''}
                
                ${alert.log_entry ? `
                <div>
                    <label class="text-gray-400 text-sm">Related Log Entry</label>
                    <div class="mt-1 text-white bg-gray-700 p-3 rounded font-mono text-xs">
                        ${alert.log_entry.raw_log || 'N/A'}
                    </div>
                </div>
                ` : ''}
                
                <div class="flex space-x-4 pt-4">
                    ${!alert.resolved ? `
                    <button onclick="addAlertNote('${alertId}')" 
                            class="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded">
                        Add Note
                    </button>
                    ${!alert.acknowledged ? `
                    <button onclick="acknowledgeAlert('${alertId}'); closeAlertModal();" 
                            class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">
                        Acknowledge
                    </button>
                    ` : ''}
                    <button onclick="resolveAlert('${alertId}'); closeAlertModal();" 
                            class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded">
                        Resolve
                    </button>
                    ` : ''}
                    <button onclick="closeAlertModal()" 
                            class="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded">
                        Close
                    </button>
                </div>
            </div>
        `;
        
        modal.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading alert details:', error);
        showError('Failed to load alert details');
    }
}

/**
 * Close alert modal
 */
function closeAlertModal() {
    document.getElementById('alert-modal').classList.add('hidden');
}

/**
 * Add note to alert
 */
async function addAlertNote(alertId) {
    const note = prompt('Enter notes for this alert:');
    if (note) {
        try {
            const response = await fetch(`${API_BASE}/api/alerts/${alertId}/notes?notes=${encodeURIComponent(note)}`, {
                method: 'PUT'
            });
            
            if (response.ok) {
                showAlertDetails(alertId); // Refresh modal
            } else {
                showError('Failed to add note');
            }
        } catch (error) {
            console.error('Error adding note:', error);
            showError('Failed to add note');
        }
    }
}

/**
 * Export alerts to CSV
 */
function exportAlerts() {
    const severity = document.getElementById('severity-filter').value;
    const ruleName = document.getElementById('rule-filter').value;
    
    let url = `${API_BASE}/api/alerts/export?format=csv`;
    if (severity) url += `&severity=${severity}`;
    if (ruleName) url += `&rule_name=${ruleName}`;
    
    window.open(url, '_blank');
}

/**
 * Search logs
 */
async function searchLogs() {
    const sourceIp = document.getElementById('search-ip').value;
    const username = document.getElementById('search-username').value;
    const eventType = document.getElementById('search-event-type').value;
    
    try {
        let url = `${API_BASE}/api/logs?limit=50`;
        if (sourceIp) url += `&source_ip=${sourceIp}`;
        if (username) url += `&username=${username}`;
        if (eventType) url += `&event_type=${eventType}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        const resultsDiv = document.getElementById('log-search-results');
        const tbody = document.getElementById('log-results-body');
        
        if (data.logs && data.logs.length > 0) {
            tbody.innerHTML = data.logs.map(log => `
                <tr class="hover:bg-gray-700">
                    <td class="px-4 py-2">${new Date(log.timestamp).toLocaleString()}</td>
                    <td class="px-4 py-2 font-mono">${log.source_ip || 'N/A'}</td>
                    <td class="px-4 py-2">${log.username || 'N/A'}</td>
                    <td class="px-4 py-2">${log.event_type}</td>
                    <td class="px-4 py-2">${log.status}</td>
                    <td class="px-4 py-2">${log.country_code || 'N/A'}</td>
                </tr>
            `).join('');
            resultsDiv.classList.remove('hidden');
        } else {
            resultsDiv.classList.add('hidden');
            showError('No logs found');
        }
    } catch (error) {
        console.error('Error searching logs:', error);
        showError('Failed to search logs');
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

