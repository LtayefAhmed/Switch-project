// Global state
let isConnected = false;
let currentConfig = {
    mock_mode: true,
    switch_ip: '192.168.1.1'
};

// DOM elements
const mockModeToggle = document.getElementById('mock-mode-toggle');
const modeLabel = document.getElementById('mode-label');
const switchIpInput = document.getElementById('switch-ip');
const statusIndicator = document.getElementById('status-indicator');
const connectionStatusText = document.getElementById('connection-status-text');
const connectBtn = document.getElementById('connect-btn');
const disconnectBtn = document.getElementById('disconnect-btn');
const interfaceSelect = document.getElementById('interface-select');
const actionSelect = document.getElementById('action-select');
const executeBtn = document.getElementById('execute-btn');
const refreshInterfacesBtn = document.getElementById('refresh-interfaces-btn');
const advancedOptions = document.getElementById('advanced-options');
const maxMacInput = document.getElementById('max-mac');
const violationActionSelect = document.getElementById('violation-action');
const resultContainer = document.getElementById('result-container');
const logsContainer = document.getElementById('logs-container');
const refreshLogsBtn = document.getElementById('refresh-logs-btn');
const clearLogsBtn = document.getElementById('clear-logs-btn');
const autoRefreshLogsCheckbox = document.getElementById('auto-refresh-logs');

// Legacy form elements
const legacyIpInput = document.getElementById('legacy-ip');
const legacyUsernameInput = document.getElementById('legacy-username');
const legacyPasswordInput = document.getElementById('legacy-password');
const legacyConnectBtn = document.getElementById('legacy-connect-btn');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
    loadLogs();
    
    // Set up auto-refresh for logs
    setInterval(() => {
        if (autoRefreshLogsCheckbox.checked) {
            loadLogs();
        }
    }, 5000);
});

// Event listeners
mockModeToggle.addEventListener('change', function() {
    currentConfig.mock_mode = this.checked;
    modeLabel.textContent = this.checked ? 'Mock Mode' : 'Real Mode';
    updateConfig();
});

switchIpInput.addEventListener('change', function() {
    currentConfig.switch_ip = this.value;
    updateConfig();
});

connectBtn.addEventListener('click', connect);
disconnectBtn.addEventListener('click', disconnect);
executeBtn.addEventListener('click', executeAction);
refreshInterfacesBtn.addEventListener('click', refreshInterfaces);
refreshLogsBtn.addEventListener('click', loadLogs);
clearLogsBtn.addEventListener('click', clearLogs);
legacyConnectBtn.addEventListener('click', legacyConnect);

actionSelect.addEventListener('change', function() {
    if (this.value === 'enable') {
        advancedOptions.classList.remove('hidden');
    } else {
        advancedOptions.classList.add('hidden');
    }
});

// Legacy connection function
async function legacyConnect() {
    const ip = legacyIpInput.value.trim();
    const username = legacyUsernameInput.value.trim();
    const password = legacyPasswordInput.value.trim();

    if (!ip || !username || !password) {
        showResult('Please fill in all fields', 'error');
        return;
    }

    setLoading(legacyConnectBtn, true);

    try {
        const response = await fetch('/api/legacy-connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ip: ip,
                username: username,
                password: password
            })
        });

        const data = await response.json();
        
        if (data.success) {
            showResult(data.output, 'success');
            updateConnectionStatus(true);
        } else {
            showResult(data.message || 'Legacy connection failed', 'error');
        }
    } catch (error) {
        showResult('Legacy connection failed: ' + error.message, 'error');
    } finally {
        setLoading(legacyConnectBtn, false);
    }
}

// API functions
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        currentConfig = data;
        mockModeToggle.checked = data.mock_mode;
        modeLabel.textContent = data.mock_mode ? 'Mock Mode' : 'Real Mode';
        switchIpInput.value = data.switch_ip;
        
        updateConnectionStatus(data.connected);
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

async function updateConfig() {
    try {
        await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(currentConfig)
        });
    } catch (error) {
        console.error('Failed to update config:', error);
    }
}

async function connect() {
    setLoading(connectBtn, true);
    
    try {
        const response = await fetch('/api/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateConnectionStatus(true);
            showResult(data.message, 'success');
            await refreshInterfaces();
        } else {
            showResult(data.message, 'error');
        }
    } catch (error) {
        showResult('Connection failed: ' + error.message, 'error');
    } finally {
        setLoading(connectBtn, false);
    }
}

async function disconnect() {
    setLoading(disconnectBtn, true);
    
    try {
        const response = await fetch('/api/disconnect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        updateConnectionStatus(false);
        showResult(data.message, 'success');
        
        // Clear interface options
        interfaceSelect.innerHTML = '<option value="">Select Interface</option>';
    } catch (error) {
        showResult('Disconnect failed: ' + error.message, 'error');
    } finally {
        setLoading(disconnectBtn, false);
    }
}

async function refreshInterfaces() {
    if (!isConnected) return;
    
    setLoading(refreshInterfacesBtn, true);
    
    try {
        const response = await fetch('/api/interfaces');
        const data = await response.json();
        
        if (data.interfaces) {
            interfaceSelect.innerHTML = '<option value="">Select Interface</option>';
            data.interfaces.forEach(interface => {
                const option = document.createElement('option');
                option.value = interface;
                option.textContent = interface;
                interfaceSelect.appendChild(option);
            });
        }
    } catch (error) {
        showResult('Failed to refresh interfaces: ' + error.message, 'error');
    } finally {
        setLoading(refreshInterfacesBtn, false);
    }
}

async function executeAction() {
    const interface = interfaceSelect.value;
    const action = actionSelect.value;
    
    if (!interface || !action) {
        showResult('Please select both interface and action', 'error');
        return;
    }
    
    setLoading(executeBtn, true);
    
    const requestData = {
        interface: interface,
        action: action
    };
    
    // Add advanced options for enable action
    if (action === 'enable') {
        requestData.max_mac = parseInt(maxMacInput.value);
        requestData.violation_action = violationActionSelect.value;
    }
    
    try {
        const response = await fetch('/api/port-security', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showResult(data.result, 'success');
        } else {
            showResult(data.result, 'error');
        }
    } catch (error) {
        showResult('Action failed: ' + error.message, 'error');
    } finally {
        setLoading(executeBtn, false);
    }
}

async function loadLogs() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();
        
        logsContainer.innerHTML = '';
        
        if (data.logs && data.logs.length > 0) {
            data.logs.forEach(log => {
                const logEntry = document.createElement('div');
                logEntry.className = 'log-entry';
                logEntry.innerHTML = `
                    <span class="log-timestamp">${log.timestamp}</span>
                    <span class="log-level ${log.level}">${log.level}</span>
                    <span class="log-message">${log.message}</span>
                `;
                logsContainer.appendChild(logEntry);
            });
            
            // Auto-scroll to bottom
            logsContainer.scrollTop = logsContainer.scrollHeight;
        } else {
            logsContainer.innerHTML = '<div class="log-entry">No logs available</div>';
        }
    } catch (error) {
        console.error('Failed to load logs:', error);
    }
}

async function clearLogs() {
    try {
        await fetch('/api/logs/clear', {
            method: 'POST'
        });
        loadLogs();
    } catch (error) {
        console.error('Failed to clear logs:', error);
    }
}

// Helper functions
function updateConnectionStatus(connected) {
    isConnected = connected;
    
    if (connected) {
        statusIndicator.classList.add('connected');
        connectionStatusText.textContent = 'Connected';
        connectBtn.disabled = true;
        disconnectBtn.disabled = false;
        executeBtn.disabled = false;
        refreshInterfacesBtn.disabled = false;
    } else {
        statusIndicator.classList.remove('connected');
        connectionStatusText.textContent = 'Disconnected';
        connectBtn.disabled = false;
        disconnectBtn.disabled = true;
        executeBtn.disabled = true;
        refreshInterfacesBtn.disabled = true;
    }
}

function showResult(message, type) {
    resultContainer.textContent = message;
    resultContainer.className = 'result-container';
    
    if (type === 'success') {
        resultContainer.classList.add('result-success');
    } else if (type === 'error') {
        resultContainer.classList.add('result-error');
    }
    
    // Auto-refresh logs to show latest activity
    if (autoRefreshLogsCheckbox.checked) {
        setTimeout(loadLogs, 1000);
    }
}

function setLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        const originalText = button.textContent;
        button.innerHTML = '<span class="loading"></span> ' + originalText;
        button.setAttribute('data-original-text', originalText);
    } else {
        button.disabled = false;
        const originalText = button.getAttribute('data-original-text');
        button.innerHTML = originalText;
        button.removeAttribute('data-original-text');
    }
}
