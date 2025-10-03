// Scion Multi-Material Printer Web Interface - JavaScript Utilities

// Global variables
let socket = null;
let connectionStatus = 'disconnected';
let backendStatus = 'offline';

// Dashboard view-model used to render the status cards without dumping raw JSON
const dashboardState = {
    printer: {
        status: 'Unknown',
        connected: false,
        currentLayer: 0,
        progressPercent: 0,
        currentMaterial: 'None',
        nextMaterial: 'None',
        nextChangeLayer: 0,
        mmActive: false
    },
    sequence: {
        currentStep: 0,
        totalSteps: 0,
        stepName: ''
    },
    lastUpdate: null
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    initializeAlerts();
    updateConnectionIndicator();
});

// Socket.IO connection management
function initializeSocket() {
    // Prefer pure WebSocket transport to reduce Engine.IO long-poll churn.
    const MAX_WS_FAILS_BEFORE_FALLBACK = 3;
    let wsFailures = 0;

    function connect(preferPolling = false) {
        const transports = preferPolling ? ['polling', 'websocket'] : ['websocket'];
        socket = io({
            transports,
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 10000,
            timeout: 5000,
            autoConnect: true
        });
        console.log(preferPolling ? 'Using mixed transports (polling+websocket) fallback' : 'Attempting WebSocket-only connection...');
        registerHandlers();
    }

    function registerHandlers() {
        socket.on('connect', function() {
            connectionStatus = 'connected';
            updateConnectionIndicator();
            console.log('Connected to server (id=' + socket.id + ')');
            wsFailures = 0;
        });
        socket.on('disconnect', function(reason) {
            connectionStatus = 'disconnected';
            updateConnectionIndicator();
            console.log('Disconnected from server (' + reason + ')');
        });
        socket.on('connect_error', function(error) {
            connectionStatus = 'error';
            updateConnectionIndicator();
            console.error('Connection error:', error.message || error);
            wsFailures += 1;
            if (wsFailures === MAX_WS_FAILS_BEFORE_FALLBACK) {
                console.warn('Falling back to polling+websocket due to repeated failures');
                try { socket.close(); } catch(e) {}
                setTimeout(() => connect(true), 500);
            }
        });
        socket.on('status_update', function(data) {
            updateGlobalStatus(data);
            console.log('Status update:', data);
        });
        socket.on('system_alert', function(data) {
            showAlert(data.message, data.type || 'info');
        });
        socket.on('system_status', function(data) {
            if (typeof data.print_manager_connected === 'boolean') {
                backendStatus = data.print_manager_connected ? 'online' : 'offline';
                updateBackendIndicator();
            }
        });
        socket.on('log_message', function(data) {
            const logContainer = document.getElementById('activity-log') || document.getElementById('process-log');
            if (logContainer) {
                const entry = document.createElement('div');
                const timestamp = new Date(data.timestamp || Date.now()).toLocaleTimeString();
                const level = (data.level || 'info').toLowerCase();
                const levelClass = level === 'error' ? 'text-danger' : level === 'warning' ? 'text-warning' : level === 'debug' ? 'text-muted' : 'text-info';
                entry.className = `log-entry ${levelClass}`;
                entry.textContent = `[${timestamp}] ${data.component ? '['+data.component+'] ' : ''}${data.message}`;
                logContainer.appendChild(entry);
                while (logContainer.children.length > 300) {
                    logContainer.removeChild(logContainer.firstChild);
                }
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        });
        socket.on('status_update', function(data) {
            if (data.component === 'WEBSOCKET') {
                if (data.status && data.status.toLowerCase().includes('connected')) {
                    backendStatus = 'online';
                    updateBackendIndicator();
                }
                if (data.status && data.status.toLowerCase().includes('disconnected')) {
                    backendStatus = 'offline';
                    updateBackendIndicator();
                }
            }
        });
    }

    connect(false); // initial attempt
    updateConnectionIndicator();
}

function updateConnectionIndicator() {
    const indicator = document.getElementById('connection-status');
    if (!indicator) return;
    switch(connectionStatus) {
        case 'connected':
            indicator.className = 'badge bg-success';
            indicator.innerHTML = '<i class="bi bi-circle-fill"></i> Connected';
            break;
        case 'disconnected':
            indicator.className = 'badge bg-danger';
            indicator.innerHTML = '<i class="bi bi-circle-fill"></i> Disconnected';
            break;
        case 'error':
            indicator.className = 'badge bg-warning';
            indicator.innerHTML = '<i class="bi bi-circle-fill"></i> Error';
            break;
        default:
            indicator.className = 'badge bg-secondary';
            indicator.innerHTML = '<i class="bi bi-circle-fill"></i> Connecting...';
    }
}

function updateBackendIndicator() {
    const indicator = document.getElementById('backend-status');
    if (!indicator) return;
    if (backendStatus === 'online') {
        indicator.className = 'badge bg-success';
        indicator.innerHTML = '<i class="bi bi-cpu"></i> Controller Online';
        document.body.classList.remove('controller-offline');
    } else if (backendStatus === 'offline') {
        indicator.className = 'badge bg-danger';
        indicator.innerHTML = '<i class="bi bi-cpu"></i> Controller Offline';
        document.body.classList.add('controller-offline');
    } else {
        indicator.className = 'badge bg-secondary';
        indicator.innerHTML = '<i class="bi bi-cpu"></i> Controller Unknown';
        document.body.classList.add('controller-offline');
    }
}

function toInt(value, fallback = null) {
    const parsed = parseInt(value, 10);
    return Number.isNaN(parsed) ? fallback : parsed;
}

function toFloat(value, fallback = null) {
    const parsed = parseFloat(value);
    return Number.isNaN(parsed) ? fallback : parsed;
}

function normalizePrinterStatusValue(raw) {
    if (raw === undefined || raw === null) {
        return null;
    }
    let text = String(raw);
    if (text.toLowerCase().startsWith('printer status')) {
        const parts = text.split(':');
        text = parts.length > 1 ? parts.slice(1).join(':') : parts[0];
    }
    return text.trim() || null;
}

function applyStatusSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') {
        return;
    }

    const printer = dashboardState.printer;

    const statusValue = normalizePrinterStatusValue(snapshot.printer_status);
    if (statusValue) {
        printer.status = statusValue;
    }

    if (snapshot.printer_connected !== undefined) {
        printer.connected = Boolean(snapshot.printer_connected);
    }

    if (snapshot.current_layer !== undefined) {
        const layer = toInt(snapshot.current_layer, printer.currentLayer);
        if (layer !== null) {
            printer.currentLayer = layer;
        }
    }

    if (snapshot.progress_percent !== undefined) {
        const progress = toFloat(snapshot.progress_percent, printer.progressPercent);
        if (progress !== null) {
            printer.progressPercent = progress;
        }
    }

    if (snapshot.current_material) {
        printer.currentMaterial = snapshot.current_material;
    }

    if (snapshot.next_material !== undefined) {
        printer.nextMaterial = snapshot.next_material || 'None';
    }

    if (snapshot.next_change_layer !== undefined) {
        const nextLayer = toInt(snapshot.next_change_layer, printer.nextChangeLayer);
        if (nextLayer !== null) {
            printer.nextChangeLayer = nextLayer;
        }
    }

    if (snapshot.mm_active !== undefined) {
        printer.mmActive = Boolean(snapshot.mm_active);
    }

    if (snapshot.last_update) {
        dashboardState.lastUpdate = snapshot.last_update;
    }

    if (snapshot.sequence_progress) {
        const seq = snapshot.sequence_progress;
        const currentStep = toInt(seq.current_step, dashboardState.sequence.currentStep) ?? dashboardState.sequence.currentStep;
        const totalSteps = toInt(seq.total_steps, dashboardState.sequence.totalSteps) ?? dashboardState.sequence.totalSteps;
        dashboardState.sequence.currentStep = currentStep;
        dashboardState.sequence.totalSteps = totalSteps;
        dashboardState.sequence.stepName = seq.step_name || dashboardState.sequence.stepName;
    }
}

function handleStatusEvent(event) {
    if (!event || typeof event !== 'object') {
        return;
    }

    const printer = dashboardState.printer;
    const payload = event.data || {};

    if (event.timestamp) {
        dashboardState.lastUpdate = event.timestamp;
    }

    switch (event.component) {
        case 'PRINTER_STATUS': {
            const statusValue = normalizePrinterStatusValue(payload.printer_status ?? event.status);
            if (statusValue) {
                printer.status = statusValue;
            }
            if (payload.printer_connected !== undefined) {
                printer.connected = Boolean(payload.printer_connected);
            }
            break;
        }
        case 'PROGRESS':
        case 'MONITOR': {
            if (payload.current_layer !== undefined) {
                const layer = toInt(payload.current_layer, printer.currentLayer);
                if (layer !== null) {
                    printer.currentLayer = layer;
                }
            }
            const statusValue = normalizePrinterStatusValue(payload.printer_status ?? event.status);
            if (statusValue) {
                printer.status = statusValue;
            }
            if (payload.printer_connected !== undefined) {
                printer.connected = Boolean(payload.printer_connected);
            }
            if (payload.percent_complete !== undefined) {
                const progress = toFloat(payload.percent_complete, printer.progressPercent);
                if (progress !== null) {
                    printer.progressPercent = progress;
                }
            }
            break;
        }
        case 'MATERIAL': {
            if (payload.material) {
                printer.currentMaterial = payload.material;
            }
            if (payload.next_material !== undefined) {
                printer.nextMaterial = payload.next_material || printer.nextMaterial;
            }
            if (payload.next_layer !== undefined) {
                const nextLayer = toInt(payload.next_layer, printer.nextChangeLayer);
                if (nextLayer !== null) {
                    printer.nextChangeLayer = nextLayer;
                }
            }
            break;
        }
        case 'SEQUENCE': {
            if (payload.current_step !== undefined || payload.total_steps !== undefined) {
                const currentStep = toInt(payload.current_step, dashboardState.sequence.currentStep) ?? dashboardState.sequence.currentStep;
                const totalSteps = toInt(payload.total_steps, dashboardState.sequence.totalSteps) ?? dashboardState.sequence.totalSteps;
                dashboardState.sequence.currentStep = currentStep;
                dashboardState.sequence.totalSteps = totalSteps;
                dashboardState.sequence.stepName = payload.step_name || dashboardState.sequence.stepName;
            }
            break;
        }
        case 'COMMAND': {
            if (event.status) {
                const text = event.status.toLowerCase();
                if (text.includes('start')) {
                    printer.mmActive = true;
                }
                if (text.includes('stop') || text.includes('completed')) {
                    printer.mmActive = false;
                }
            }
            break;
        }
        case 'EXPERIMENT': {
            if (event.status && event.status.toLowerCase().includes('completed')) {
                printer.mmActive = false;
            }
            break;
        }
        default:
            break;
    }
}

function formatPrinterStatusLabel(rawStatus) {
    const normalized = normalizePrinterStatusValue(rawStatus) || 'Unknown';
    const upper = normalized.toUpperCase();
    const known = {
        STOPPRN: 'Stopped',
        PRINTING: 'Printing',
        PAUSE: 'Paused',
        PAUSED: 'Paused',
        IDLE: 'Idle',
        READY: 'Ready'
    };
    if (known[upper]) {
        return known[upper];
    }
    if (upper.length > 24) {
        return upper.slice(0, 21) + '...';
    }
    return normalized.replace(/_/g, ' ');
}

function getPrinterStatusBadgeClass(status) {
    const normalized = normalizePrinterStatusValue(status);
    if (!normalized) {
        return 'bg-secondary';
    }
    const lower = normalized.toLowerCase();
    if (lower.includes('print')) {
        return 'bg-success';
    }
    if (lower.includes('pause')) {
        return 'bg-warning text-dark';
    }
    if (lower.includes('stop') || lower.includes('error') || lower.includes('fail')) {
        return 'bg-danger';
    }
    if (lower.includes('idle') || lower.includes('ready')) {
        return 'bg-info';
    }
    return 'bg-secondary';
}

function updateRecipeTableHighlights(currentLayer, nextChangeLayer) {
    const rows = document.querySelectorAll('#recipe-table tr');
    if (!rows.length) {
        return;
    }

    const current = toInt(currentLayer, 0) ?? 0;
    const next = toInt(nextChangeLayer, 0) ?? 0;

    rows.forEach(row => {
        const layerAttr = toInt(row.getAttribute('data-layer'), null);
        if (layerAttr === null) {
            return;
        }
        const statusCell = row.querySelector('td:nth-child(4)');
        if (!statusCell) {
            return;
        }

        if (current > 0 && layerAttr <= current) {
            statusCell.innerHTML = '<span class="badge bg-success">Completed</span>';
        } else if (next > 0 && layerAttr === next) {
            statusCell.innerHTML = '<span class="badge bg-warning text-dark">Next</span>';
        } else {
            statusCell.innerHTML = '<span class="badge bg-light text-dark">Pending</span>';
        }
    });
}

function renderDashboard() {
    const printer = dashboardState.printer;

    const statusEl = document.getElementById('printer-status');
    if (statusEl) {
        const label = formatPrinterStatusLabel(printer.status);
        const badgeClass = getPrinterStatusBadgeClass(printer.status);
        statusEl.innerHTML = `<span class="badge ${badgeClass}">${label}</span>`;
    }

    const layerEl = document.getElementById('current-layer');
    if (layerEl) {
        layerEl.textContent = printer.currentLayer ?? 0;
    }

    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    if (progressBar && progressText) {
        const progress = Number.isFinite(printer.progressPercent) ? Math.min(100, Math.max(0, printer.progressPercent)) : 0;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${progress.toFixed(1)}%`;
    }

    const materialEl = document.getElementById('current-material');
    if (materialEl) {
        materialEl.innerHTML = `<span class="badge bg-info">${printer.currentMaterial || 'None'}</span>`;
    }

    const nextChangeEl = document.getElementById('next-change');
    if (nextChangeEl) {
        const nextMaterial = printer.nextMaterial || 'None';
        const nextLayer = printer.nextChangeLayer || 0;
        nextChangeEl.innerHTML = `Material <strong>${nextMaterial}</strong> at layer <strong>${nextLayer}</strong>`;
    }

    const mmStatusEl = document.getElementById('mm-status');
    if (mmStatusEl) {
        mmStatusEl.innerHTML = printer.mmActive
            ? '<span class="badge bg-success">Active</span>'
            : '<span class="badge bg-secondary">Stopped</span>';
    }

    const connectionBadge = document.getElementById('printer-connection');
    if (connectionBadge) {
        connectionBadge.className = `badge ${printer.connected ? 'bg-success' : 'bg-danger'}`;
        connectionBadge.textContent = printer.connected ? 'Connected' : 'Disconnected';
    }

    const lastUpdateEl = document.getElementById('last-update');
    if (lastUpdateEl && dashboardState.lastUpdate) {
        lastUpdateEl.textContent = formatTimestamp(dashboardState.lastUpdate);
    }

    updateRecipeTableHighlights(printer.currentLayer, printer.nextChangeLayer);

    const seqBar = document.getElementById('step-progress-bar');
    const seqText = document.getElementById('step-progress-text');
    if (seqBar && seqText) {
        const { currentStep, totalSteps } = dashboardState.sequence;
        if (totalSteps > 0) {
            const percent = Math.min(100, Math.max(0, (currentStep / totalSteps) * 100));
            seqBar.style.width = `${percent}%`;
            seqText.textContent = `${currentStep}/${totalSteps}`;
        } else {
            seqBar.style.width = '0%';
            seqText.textContent = '0/0';
        }
    }
}

// Alert system
function initializeAlerts() {
    // Create alert container if it doesn't exist
    if (!document.getElementById('alert-container')) {
        const container = document.createElement('div');
        container.id = 'alert-container';
        container.className = 'container mt-3';
        document.body.insertBefore(container, document.body.firstChild);
    }
}

function showAlert(message, type = 'info', timeout = 5000) {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;

    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show fade-in`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Add to container
    alertContainer.appendChild(alert);

    // Auto-dismiss after timeout
    if (timeout > 0) {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.classList.remove('show');
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 150);
            }
        }, timeout);
    }

    // Remove old alerts if too many
    const alerts = alertContainer.querySelectorAll('.alert');
    if (alerts.length > 3) {
        alerts[0].remove();
    }
}

// API utilities
function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const mergedOptions = { ...defaultOptions, ...options };

    return fetch(endpoint, mergedOptions)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('API call failed:', error);
            showAlert(`API Error: ${error.message}`, 'danger');
            throw error;
        });
}

// Utility functions
function formatTimestamp(timestamp) {
    if (!timestamp) return '--:--';

    const date = new Date(timestamp);
    return date.toLocaleTimeString();
}

function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function validateRecipeFormat(recipeText) {
    if (!recipeText || !recipeText.trim()) {
        return { valid: false, error: 'Recipe cannot be empty' };
    }

    const entries = recipeText.split(':');
    const layers = [];

    for (const entry of entries) {
        if (!entry.includes(',')) {
            return { valid: false, error: `Invalid format in entry: ${entry}` };
        }

        const [material, layer] = entry.split(',', 2);
        const materialTrimmed = material.trim().toUpperCase();
        const layerNum = parseInt(layer.trim());

        if (!['A', 'B', 'C', 'D'].includes(materialTrimmed)) {
            return { valid: false, error: `Invalid material: ${materialTrimmed}` };
        }

        if (isNaN(layerNum) || layerNum <= 0) {
            return { valid: false, error: `Invalid layer number: ${layer.trim()}` };
        }

        if (layers.includes(layerNum)) {
            return { valid: false, error: `Duplicate layer: ${layerNum}` };
        }

        layers.push(layerNum);
    }

    return { valid: true, layers: layers.length };
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showAlert('Copied to clipboard', 'success', 2000);
        }).catch(err => {
            console.error('Failed to copy: ', err);
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showAlert('Copied to clipboard', 'success', 2000);
        } else {
            showAlert('Failed to copy to clipboard', 'warning');
        }
    } catch (err) {
        showAlert('Copy not supported by browser', 'warning');
    }

    document.body.removeChild(textArea);
}

// Data storage utilities
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
        return false;
    }
}

function loadFromLocalStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.error('Failed to load from localStorage:', error);
        return defaultValue;
    }
}

// Form validation utilities
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    const errors = [];

    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            errors.push(`${input.name || input.id} is required`);
            input.classList.add('is-invalid');
        } else {
            input.classList.remove('is-invalid');
        }

        // Type-specific validation
        if (input.type === 'number' && input.value) {
            const num = parseFloat(input.value);
            const min = parseFloat(input.min);
            const max = parseFloat(input.max);

            if (!isNaN(min) && num < min) {
                isValid = false;
                errors.push(`${input.name || input.id} must be at least ${min}`);
                input.classList.add('is-invalid');
            }

            if (!isNaN(max) && num > max) {
                isValid = false;
                errors.push(`${input.name || input.id} must be no more than ${max}`);
                input.classList.add('is-invalid');
            }
        }
    });

    return { isValid, errors };
}

// Loading state management
function setLoadingState(element, loading = true) {
    if (loading) {
        element.disabled = true;
        element.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    } else {
        element.disabled = false;
        // Restore original content - this would need to be enhanced to store original text
    }
}

// Theme management (for future dark mode support)
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

function loadSavedTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

// Debug utilities
function debugLog(message, data = null) {
    if (window.location.search.includes('debug=true')) {
        console.log(`[DEBUG] ${message}`, data);
    }
}

function enableDebugMode() {
    window.debugMode = true;
    console.log('Debug mode enabled');
    showAlert('Debug mode enabled - check console for detailed logs', 'info');
}

// Quick Action Functions (see Dashboard Quick Actions section for updated implementations)

function quickPumpTest() {
    if (confirm('Run a quick test of all pumps? This will run each pump briefly.')) {
        const btn = document.getElementById('test-pumps-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Testing...';
        }

        fetch('/api/test_pumps', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Pump test completed successfully!', 'success');
            } else {
                showAlert(`Pump test failed: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            showAlert(`Error: ${error.message}`, 'danger');
        })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-gear"></i> Test Pumps';
            }
        });
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Ctrl+Enter: Start/Stop multi-material
    if (event.ctrlKey && event.key === 'Enter') {
        event.preventDefault();
        const statusElement = document.getElementById('mm-status');
        if (statusElement && statusElement.textContent.includes('Active')) {
            stopMultiMaterial();
        } else {
            startMultiMaterial();
        }
    }

    // Ctrl+T: Test pumps
    if (event.ctrlKey && event.key === 't') {
        event.preventDefault();
        quickPumpTest();
    }

    // Escape: Emergency stop
    if (event.key === 'Escape') {
        event.preventDefault();
        if (confirm('Emergency stop - halt all operations?')) {
            fetch('/api/emergency_stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    showAlert('Emergency stop activated!', 'warning');
                });
        }
    }
});

// Error handling
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    if (window.debugMode) {
        showAlert(`JavaScript Error: ${event.error.message}`, 'danger');
    }
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    if (window.debugMode) {
        showAlert(`Promise Rejection: ${event.reason}`, 'danger');
    }
});

// Performance monitoring
function logPerformance(label) {
    if (window.debugMode && performance.mark) {
        performance.mark(label);
    }
}

// Global status update handler
function updateGlobalStatus(data) {
    if (!data) {
        return;
    }

    if (data.component !== undefined) {
        handleStatusEvent(data);
    } else if (typeof data === 'object') {
        applyStatusSnapshot(data);
    }

    // Update timing information
    if (data.operation_duration !== undefined) {
        const durationElement = document.getElementById('operation-duration');
        if (durationElement) {
            durationElement.textContent = data.operation_duration.toFixed(1) + 's';
        }
    }

    if (data.current_operation !== undefined) {
        const operationElement = document.getElementById('operation-badge');
        if (operationElement) {
            operationElement.textContent = data.current_operation || 'idle';

            operationElement.className = 'badge';
            if (data.current_operation === 'idle') {
                operationElement.classList.add('bg-secondary');
            } else if (data.current_operation.includes('error')) {
                operationElement.classList.add('bg-danger');
            } else if (data.current_operation.includes('completed')) {
                operationElement.classList.add('bg-success');
            } else {
                operationElement.classList.add('bg-warning');
            }
        }
    }

    if (data.operation_start_time) {
        const startElement = document.getElementById('operation-start');
        if (startElement) {
            startElement.textContent = formatTimestamp(data.operation_start_time);
        }
    }

    if (data.pump_status) {
        Object.entries(data.pump_status).forEach(([pumpId, status]) => {
            const statusElement = document.getElementById(`${pumpId}-status`);
            const indicatorElement = document.getElementById(`${pumpId}-indicator`);

            if (statusElement) {
                statusElement.textContent = status;
                statusElement.className = 'badge';
                if (status === 'idle') {
                    statusElement.classList.add('bg-secondary');
                } else if (status.includes('running')) {
                    statusElement.classList.add('bg-warning');
                } else if (status.includes('error')) {
                    statusElement.classList.add('bg-danger');
                } else {
                    statusElement.classList.add('bg-info');
                }
            }

            if (indicatorElement) {
                const icon = indicatorElement.querySelector('i');
                if (icon) {
                    icon.className = 'bi fs-2';
                    if (status === 'idle') {
                        icon.classList.add('bi-droplet', 'text-muted');
                    } else if (status.includes('running')) {
                        icon.classList.add('bi-droplet-fill', 'text-warning');
                    } else if (status.includes('error')) {
                        icon.classList.add('bi-droplet-fill', 'text-danger');
                    } else {
                        icon.classList.add('bi-droplet-fill', 'text-info');
                    }
                }
            }
        });
    }

    if (data.sequence_progress) {
        const progressBar = document.getElementById('step-progress-bar');
        const progressText = document.getElementById('step-progress-text');

        if (progressBar && data.sequence_progress.total_steps > 0) {
            const progress = (data.sequence_progress.current_step / data.sequence_progress.total_steps) * 100;
            progressBar.style.width = `${progress}%`;
        }

        if (progressText) {
            progressText.textContent = `${data.sequence_progress.current_step}/${data.sequence_progress.total_steps}`;
        }
    }

    renderDashboard();
    startTimerUpdates(data.operation_start_time);
}

// Live timer updates
let timerInterval = null;

function startTimerUpdates(startTime) {
    if (timerInterval) {
        clearInterval(timerInterval);
    }

    if (!startTime || startTime === '--:--') {
        return;
    }

    timerInterval = setInterval(() => {
        const start = new Date(startTime);
        const now = new Date();
        const duration = (now - start) / 1000;

        const durationElement = document.getElementById('operation-duration');
        if (durationElement) {
            durationElement.textContent = duration.toFixed(1) + 's';
        }
    }, 1000);
}

// Export functions for use in other scripts
window.ScionApp = {
    showAlert,
    apiCall,
    validateRecipeFormat,
    copyToClipboard,
    saveToLocalStorage,
    loadFromLocalStorage,
    validateForm,
    setLoadingState,
    debugLog,
    enableDebugMode,
    formatTimestamp,
    formatDuration,
    updateGlobalStatus,
    applyStatusSnapshot,
    handleStatusEvent,
    renderDashboard,
    updateRecipeTableHighlights,
    printerControl
};

// Dashboard Quick Actions
async function startMultiMaterial() {
    const button = document.getElementById('start-print-btn');
    const originalText = button.innerHTML;

    try {
        // Confirmation dialog
        if (!confirm('Start multi-material printing with the current recipe?')) {
            return;
        }

        // Update button state
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Starting...';

        const response = await fetch('/api/multi-material/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.success) {
            showAlert('Multi-material printing started successfully!', 'success');
            button.innerHTML = '<i class="bi bi-check-circle-fill"></i> Started';
            setTimeout(() => {
                button.innerHTML = '<i class="bi bi-stop-fill"></i> Stop Multi-Material';
                button.onclick = stopMultiMaterial;
                button.className = 'btn btn-danger btn-lg w-100';
                button.disabled = false;
            }, 2000);
        } else {
            throw new Error(result.message || 'Failed to start multi-material printing');
        }
    } catch (error) {
        console.error('Error starting multi-material printing:', error);
        showAlert(`Error: ${error.message}`, 'danger');
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

async function stopMultiMaterial() {
    const button = document.getElementById('start-print-btn');

    try {
        if (!confirm('Stop multi-material printing?')) {
            return;
        }

        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Stopping...';

        const response = await fetch('/api/multi-material/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.success) {
            showAlert('Multi-material printing stopped', 'warning');
            button.innerHTML = '<i class="bi bi-play-fill"></i> Start Multi-Material';
            button.onclick = startMultiMaterial;
            button.className = 'btn btn-success btn-lg w-100';
            button.disabled = false;
        } else {
            throw new Error(result.message || 'Failed to stop printing');
        }
    } catch (error) {
        console.error('Error stopping multi-material printing:', error);
        showAlert(`Error: ${error.message}`, 'danger');
        button.disabled = false;
    }
}

async function printerControl(action) {
    if (!action) {
        return;
    }

    const actionLower = action.toLowerCase();
    const actionText = actionLower.charAt(0).toUpperCase() + actionLower.slice(1);

    try {
        showAlert(`${actionText}ing printer...`, 'info');

        const response = await fetch(`/api/printer/${actionLower}`, { method: 'POST' });
        const result = await response.json();

        if (result.success) {
            showAlert(`Printer ${actionLower}d successfully`, 'success');
        } else {
            throw new Error(result.message || `Failed to ${actionLower} printer`);
        }
    } catch (error) {
        console.error(`Error ${actionLower}ing printer:`, error);
        const message = error instanceof Error ? error.message : String(error);
        showAlert(`Error ${actionLower}ing printer: ${message}`, 'danger');
    }
}

async function quickPumpTest() {
    try {
        if (!confirm('Test all pumps? This will run each pump for 3 seconds.')) {
            return;
        }

        showAlert('Starting pump test sequence...', 'info');

        const pumps = ['A', 'B', 'C', 'D'];
        for (const pump of pumps) {
            showAlert(`Testing Pump ${pump}...`, 'info', 2000);

            const response = await fetch('/api/pump', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    motor: pump,
                    direction: 'F',
                    duration: 3
                })
            });

            const result = await response.json();
            if (!result.success) {
                throw new Error(`Pump ${pump} test failed: ${result.message}`);
            }

            // Wait a bit between pump tests
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        showAlert('All pumps tested successfully!', 'success');
    } catch (error) {
        console.error('Error during pump test:', error);
        showAlert(`Pump test error: ${error.message}`, 'danger');
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Ctrl/Cmd + Enter = Start/Stop print
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        const startBtn = document.getElementById('start-print-btn');
        if (startBtn && !startBtn.disabled) {
            startBtn.click();
        }
    }

    // Ctrl/Cmd + T = Test pumps
    if ((event.ctrlKey || event.metaKey) && event.key === 't') {
        event.preventDefault();
        quickPumpTest();
    }

    // Escape = Emergency stop
    if (event.key === 'Escape') {
        event.preventDefault();
        emergencyStop();
    }
});

async function emergencyStop() {
    try {
        const response = await fetch('/api/emergency-stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        if (result.success) {
            showAlert('EMERGENCY STOP ACTIVATED', 'danger');
        }
    } catch (error) {
        console.error('Error during emergency stop:', error);
    }
}

// Add tooltips to show keyboard shortcuts
document.addEventListener('DOMContentLoaded', function() {
    const startBtn = document.getElementById('start-print-btn');
    if (startBtn) {
        startBtn.title = 'Ctrl+Enter to start/stop';
    }
});

// Initialize theme on load
loadSavedTheme();

// ==========================================
// PRINT FILE MANAGEMENT FUNCTIONS
// ==========================================

let selectedPrintFile = null;

// Refresh print files list
async function refreshPrintFiles() {
    const loadingDiv = document.getElementById('print-files-loading');
    const emptyDiv = document.getElementById('print-files-empty');
    const errorDiv = document.getElementById('print-files-error');
    const listDiv = document.getElementById('print-files-list');
    const refreshBtn = document.getElementById('refresh-files-btn');

    // Show loading state
    hideAllFileStates();
    loadingDiv.style.display = 'block';
    refreshBtn.disabled = true;

    try {
        const response = await fetch('/api/printer/files');
        const result = await response.json();

        if (result.success) {
            if (result.files && result.files.length > 0) {
                displayPrintFiles(result.files);
                listDiv.style.display = 'block';
            } else {
                emptyDiv.style.display = 'block';
            }
        } else {
            showFileError(result.message || 'Failed to load print files');
        }
    } catch (error) {
        console.error('Error fetching print files:', error);
        showFileError('Network error: Could not connect to printer');
    } finally {
        loadingDiv.style.display = 'none';
        refreshBtn.disabled = false;
    }
}

// Display print files in the UI
function displayPrintFiles(files) {
    const listDiv = document.getElementById('print-files-list');
    listDiv.innerHTML = '';

    files.forEach(file => {
        const fileCard = createFileCard(file);
        listDiv.appendChild(fileCard);
    });
}

// Create a file card element
function createFileCard(file) {
    const colDiv = document.createElement('div');
    colDiv.className = 'col-md-6 col-lg-4 mb-3';

    const cardDiv = document.createElement('div');
    cardDiv.className = 'card file-card h-100';
    cardDiv.style.cursor = 'pointer';
    cardDiv.onclick = () => selectPrintFile(file, cardDiv);

    const fileSize = formatFileSize(file.size);
    const fileType = file.type || 'Unknown';

    cardDiv.innerHTML = `
        <div class="card-body p-3">
            <div class="d-flex align-items-start">
                <div class="file-icon me-3">
                    <i class="bi bi-file-earmark-text fs-2 text-primary"></i>
                </div>
                <div class="file-info flex-grow-1">
                    <h6 class="card-title mb-1 text-truncate" title="${file.name}">${file.name}</h6>
                    <p class="card-text small text-muted mb-1">
                        <i class="bi bi-hdd"></i> ${fileSize}
                    </p>
                    <p class="card-text small text-muted mb-0">
                        <i class="bi bi-file-earmark"></i> ${fileType}
                    </p>
                </div>
            </div>
        </div>
        <div class="card-footer p-2 d-none file-actions">
            <button class="btn btn-success btn-sm w-100" onclick="event.stopPropagation(); startPrintFile('${file.name}')">
                <i class="bi bi-play-fill"></i> Start Print
            </button>
        </div>
    `;

    colDiv.appendChild(cardDiv);
    return colDiv;
}

// Select a print file
function selectPrintFile(file, cardElement) {
    // Clear previous selection
    document.querySelectorAll('.file-card').forEach(card => {
        card.classList.remove('border-success', 'bg-light');
        card.querySelector('.file-actions')?.classList.add('d-none');
    });

    // Select new file
    selectedPrintFile = file;
    cardElement.classList.add('border-success', 'bg-light');
    cardElement.querySelector('.file-actions')?.classList.remove('d-none');

    // Update selected file info
    updateSelectedFileInfo(file);
}

// Update selected file info display
function updateSelectedFileInfo(file) {
    const infoDiv = document.getElementById('selected-file-info');
    const nameSpan = document.getElementById('selected-file-name');
    const sizeSpan = document.getElementById('selected-file-size');
    const typeSpan = document.getElementById('selected-file-type');

    nameSpan.textContent = file.name;
    sizeSpan.textContent = formatFileSize(file.size);
    typeSpan.textContent = file.type || 'Unknown';

    infoDiv.style.display = 'block';
}

// Clear file selection
function clearFileSelection() {
    selectedPrintFile = null;
    document.querySelectorAll('.file-card').forEach(card => {
        card.classList.remove('border-success', 'bg-light');
        card.querySelector('.file-actions')?.classList.add('d-none');
    });
    document.getElementById('selected-file-info').style.display = 'none';
}

// Start printing selected file
async function startSelectedPrint() {
    if (!selectedPrintFile) {
        showAlert('No file selected', 'warning');
        return;
    }

    await startPrintFile(selectedPrintFile.name);
}

// Start printing a specific file
async function startPrintFile(filename) {
    if (!confirm(`Start printing "${filename}"?\n\nThis will begin the print job on the printer.`)) {
        return;
    }

    const btn = document.getElementById('start-selected-print-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Starting...';
    }

    try {
        const response = await fetch('/api/printer/start-print', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ filename: filename })
        });

        const result = await response.json();

        if (result.success) {
            showAlert(`Print started: ${filename}`, 'success');
            clearFileSelection();
        } else {
            showAlert(`Failed to start print: ${result.message}`, 'danger');
        }
    } catch (error) {
        console.error('Error starting print:', error);
        showAlert('Network error: Could not start print', 'danger');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-play-fill"></i> Start Print';
        }
    }
}

// Show upload modal (placeholder)
function showUploadModal() {
    showAlert('File upload functionality coming soon!', 'info');
}

// Helper functions
function hideAllFileStates() {
    document.getElementById('print-files-loading').style.display = 'none';
    document.getElementById('print-files-empty').style.display = 'none';
    document.getElementById('print-files-error').style.display = 'none';
    document.getElementById('print-files-list').style.display = 'none';
}

function showFileError(message) {
    hideAllFileStates();
    const errorDiv = document.getElementById('print-files-error');
    const errorMsg = document.getElementById('print-files-error-message');
    errorMsg.textContent = message;
    errorDiv.style.display = 'block';
}

function formatFileSize(bytes) {
    if (bytes === 0 || !bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Initialize print files on page load
document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh print files when page loads
    if (document.getElementById('print-files-list')) {
        setTimeout(refreshPrintFiles, 1000); // Delay to let page fully load
    }
});