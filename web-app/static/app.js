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
        totalLayers: 0,
        progressPercent: 0,
        secondsElapsed: null,
        secondsRemaining: null,
        printStartTime: null,  // Track when print started for elapsed calculation
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

// Update elapsed time based on start time
let elapsedTimeInterval = null;
function startElapsedTimer() {
    if (elapsedTimeInterval) {
        clearInterval(elapsedTimeInterval);
    }
    elapsedTimeInterval = setInterval(() => {
        if (dashboardState.printer.printStartTime) {
            const elapsed = Math.floor((Date.now() - dashboardState.printer.printStartTime) / 1000);
            dashboardState.printer.secondsElapsed = elapsed;
            renderDashboard();
        }
    }, 1000);
}

function stopElapsedTimer() {
    if (elapsedTimeInterval) {
        clearInterval(elapsedTimeInterval);
        elapsedTimeInterval = null;
    }
    dashboardState.printer.printStartTime = null;
    dashboardState.printer.secondsElapsed = null;
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    initializeAlerts();
    updateConnectionIndicator();

    // Export socket globally for use in page-specific scripts
    window.socket = socket;
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
        socket.on('file_list_response', handleFileListResponse);
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
        indicator.style.cursor = 'default';
        indicator.onclick = null;
        document.body.classList.remove('controller-offline');
    } else if (backendStatus === 'offline') {
        indicator.className = 'badge bg-danger';
        indicator.innerHTML = '<i class="bi bi-cpu"></i> Controller Offline';
        indicator.style.cursor = 'pointer';
        indicator.onclick = restartPrintManager;
        indicator.title = 'Click to restart controller';
        document.body.classList.add('controller-offline');
    } else {
        indicator.className = 'badge bg-secondary';
        indicator.innerHTML = '<i class="bi bi-cpu"></i> Controller Unknown';
        indicator.style.cursor = 'pointer';
        indicator.onclick = restartPrintManager;
        indicator.title = 'Click to restart controller';
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

    if (snapshot.total_layers !== undefined) {
        const totalLayers = toInt(snapshot.total_layers, printer.totalLayers);
        if (totalLayers !== null) {
            printer.totalLayers = totalLayers;
        }
    }

    if (snapshot.progress_percent !== undefined) {
        const progress = toFloat(snapshot.progress_percent, printer.progressPercent);
        if (progress !== null) {
            printer.progressPercent = progress;
        }
    }

    // Note: We calculate elapsed time client-side from print start
    // Only take remaining time from printer
    if (snapshot.seconds_remaining !== undefined) {
        printer.secondsRemaining = toInt(snapshot.seconds_remaining, printer.secondsRemaining);
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
                const prevStatus = printer.status;
                printer.status = statusValue;

                // Start elapsed timer when print starts
                const lower = statusValue.toLowerCase();
                if ((lower === 'print' || lower === 'printing') && prevStatus !== statusValue) {
                    if (!printer.printStartTime) {
                        printer.printStartTime = Date.now();
                        startElapsedTimer();
                    }
                }

                // Reset state when printer is stopped
                if (lower === 'stopprn' || lower === 'stopped' || lower === 'idle' || lower === 'ready') {
                    stopElapsedTimer();
                    printer.currentLayer = 0;
                    printer.totalLayers = 0;
                    printer.progressPercent = 0;
                    printer.secondsElapsed = null;
                    printer.secondsRemaining = null;
                    printer.currentMaterial = 'None';
                    printer.nextMaterial = 'None';
                    printer.nextChangeLayer = 0;
                    printer.mmActive = false;
                }
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
            if (payload.total_layers !== undefined) {
                const totalLayers = toInt(payload.total_layers, printer.totalLayers);
                if (totalLayers !== null) {
                    printer.totalLayers = totalLayers;
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
            // Only take remaining time from printer (elapsed calculated client-side)
            if (payload.seconds_remaining !== undefined) {
                printer.secondsRemaining = toInt(payload.seconds_remaining, printer.secondsRemaining);
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
        const currentLayer = printer.currentLayer ?? 0;
        const totalLayers = printer.totalLayers ?? 0;

        if (totalLayers > 0) {
            const layerPercent = ((currentLayer / totalLayers) * 100).toFixed(1);
            layerEl.textContent = `${currentLayer} / ${totalLayers} (${layerPercent}%)`;
        } else {
            layerEl.textContent = currentLayer;
        }
    }

    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    if (progressBar && progressText) {
        const progress = Number.isFinite(printer.progressPercent) ? Math.min(100, Math.max(0, printer.progressPercent)) : 0;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${progress.toFixed(1)}%`;
    }

    const elapsedEl = document.getElementById('time-elapsed');
    if (elapsedEl) {
        if (printer.secondsElapsed !== null && printer.secondsElapsed !== undefined) {
            elapsedEl.textContent = formatDuration(printer.secondsElapsed);
        } else {
            elapsedEl.textContent = '--';
        }
    }

    const remainingEl = document.getElementById('time-remaining');
    if (remainingEl) {
        if (printer.secondsRemaining !== null && printer.secondsRemaining !== undefined) {
            remainingEl.textContent = formatDuration(printer.secondsRemaining);
        } else {
            remainingEl.textContent = '--';
        }
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
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    // Map alert types to Bootstrap toast colors and icons
    const typeMap = {
        'success': { bg: 'success', icon: 'check-circle-fill' },
        'danger': { bg: 'danger', icon: 'exclamation-triangle-fill' },
        'warning': { bg: 'warning', icon: 'exclamation-circle-fill' },
        'info': { bg: 'info', icon: 'info-circle-fill' },
        'primary': { bg: 'primary', icon: 'bell-fill' },
        'secondary': { bg: 'secondary', icon: 'gear-fill' }
    };

    const config = typeMap[type] || typeMap['info'];

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${config.bg} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi bi-${config.icon} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    // Add to container
    toastContainer.appendChild(toast);

    // Initialize Bootstrap toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: timeout
    });

    bsToast.show();

    // Remove from DOM after hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });

    // Remove old toasts if too many (keep max 5)
    const toasts = toastContainer.querySelectorAll('.toast');
    if (toasts.length > 5) {
        toasts[0].remove();
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

    // Extract payload data - could be at top level or in data.data
    const payload = data.data || data;

    if (data.component !== undefined) {
        handleStatusEvent(data);
    } else if (typeof data === 'object') {
        applyStatusSnapshot(data);
    }

    // Update timing information
    if (payload.operation_duration !== undefined) {
        const durationElement = document.getElementById('operation-duration');
        if (durationElement) {
            durationElement.textContent = payload.operation_duration.toFixed(1) + 's';
        }
    }

    if (payload.current_operation !== undefined) {
        const operationElement = document.getElementById('operation-badge');
        if (operationElement) {
            operationElement.textContent = payload.current_operation || 'idle';

            operationElement.className = 'badge';
            if (payload.current_operation === 'idle') {
                operationElement.classList.add('bg-secondary');
            } else if (payload.current_operation.includes('error')) {
                operationElement.classList.add('bg-danger');
            } else if (payload.current_operation.includes('completed')) {
                operationElement.classList.add('bg-success');
            } else {
                operationElement.classList.add('bg-warning');
            }
        }
    }

    if (payload.operation_start_time) {
        const startElement = document.getElementById('operation-start');
        if (startElement) {
            startElement.textContent = formatTimestamp(payload.operation_start_time);
        }
    }

    if (payload.pump_status) {
        Object.entries(payload.pump_status).forEach(([pumpId, status]) => {
            // Convert pump_a to pump-a for HTML element IDs
            const elementId = pumpId.replace(/_/g, '-');
            const statusElement = document.getElementById(`${elementId}-status`);
            const indicatorElement = document.getElementById(`${elementId}-indicator`);

            if (statusElement) {
                statusElement.textContent = status;
                statusElement.className = 'badge';
                if (status === 'idle') {
                    statusElement.classList.add('bg-secondary');
                } else if (status.includes('running')) {
                    statusElement.classList.add('bg-success');
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
                        icon.classList.add('bi-droplet-fill', 'text-success');
                    } else if (status.includes('error')) {
                        icon.classList.add('bi-droplet-fill', 'text-danger');
                    } else {
                        icon.classList.add('bi-droplet-fill', 'text-info');
                    }
                }
            }
        });
    }

    if (payload.sequence_progress) {
        const progressBar = document.getElementById('step-progress-bar');
        const progressText = document.getElementById('step-progress-text');

        if (progressBar && payload.sequence_progress.total_steps > 0) {
            const progress = (payload.sequence_progress.current_step / payload.sequence_progress.total_steps) * 100;
            progressBar.style.width = `${progress}%`;
        }

        if (progressText) {
            progressText.textContent = `${payload.sequence_progress.current_step}/${payload.sequence_progress.total_steps}`;
        }
    }

    renderDashboard();
    startTimerUpdates(payload.operation_start_time);
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

async function restartPrintManager() {
    if (!confirm('Restart the print manager controller?\n\nThis will temporarily interrupt monitoring and control.')) {
        return;
    }

    const indicator = document.getElementById('backend-status');
    const originalHtml = indicator.innerHTML;

    try {
        indicator.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Restarting...';
        indicator.style.cursor = 'wait';
        indicator.onclick = null;

        const response = await fetch('/api/restart-print-manager', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.success) {
            showAlert('Print manager restart initiated', 'info');
        } else {
            throw new Error(result.message || 'Failed to restart print manager');
        }
    } catch (error) {
        console.error('Error restarting print manager:', error);
        showAlert(`Error: ${error.message}`, 'danger');
        indicator.innerHTML = originalHtml;
        updateBackendIndicator();
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
let pendingFileRequestId = null;
let pendingFileRequestTimer = null;

function processFileListResult(result) {
    const { success, files = [], message = '' } = result || {};
    const loadingDiv = document.getElementById('print-files-loading');
    const listDiv = document.getElementById('print-files-list');
    const emptyDiv = document.getElementById('print-files-empty');
    const errorDiv = document.getElementById('print-files-error');
    const refreshBtn = document.getElementById('refresh-files-btn');

    if (pendingFileRequestTimer) {
        clearTimeout(pendingFileRequestTimer);
        pendingFileRequestTimer = null;
    }
    pendingFileRequestId = null;

    if (loadingDiv) {
        loadingDiv.style.display = 'none';
    }
    if (refreshBtn) {
        refreshBtn.disabled = false;
    }

    hideAllFileStates();
    clearFileSelection();

    if (!success) {
        showFileError(message || 'Failed to load print files');
        return;
    }

    if (Array.isArray(files) && files.length > 0) {
        displayPrintFiles(files);
        if (listDiv) {
            listDiv.style.display = 'block';
        }
    } else {
        if (emptyDiv) {
            emptyDiv.style.display = 'block';
        }
    }

    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
}

function handleFileListResponse(event) {
    if (!event || typeof event !== 'object') {
        return;
    }

    const commandId = event.command_id || event.commandId || null;
    if (pendingFileRequestId && commandId && commandId !== pendingFileRequestId) {
        return;
    }

    processFileListResult({
        success: Boolean(event.success),
        files: Array.isArray(event.files) ? event.files : [],
        message: event.message || ''
    });
}

// Refresh print files list
async function refreshPrintFiles() {
    const loadingDiv = document.getElementById('print-files-loading');
    const refreshBtn = document.getElementById('refresh-files-btn');

    // Show loading state
    hideAllFileStates();
    if (loadingDiv) {
        loadingDiv.style.display = 'block';
    }
    if (refreshBtn) {
        refreshBtn.disabled = true;
    }

    try {
        const response = await fetch('/api/printer/files');
        const result = await response.json();

        if (result.success) {
            if (Array.isArray(result.files)) {
                processFileListResult({ success: true, files: result.files });
            } else if (result.command_id) {
                pendingFileRequestId = result.command_id;
                if (pendingFileRequestTimer) {
                    clearTimeout(pendingFileRequestTimer);
                }
                pendingFileRequestTimer = setTimeout(() => {
                    if (pendingFileRequestId === result.command_id) {
                        processFileListResult({ success: false, message: 'Timed out waiting for printer response' });
                    }
                }, 10000);
            } else {
                processFileListResult({ success: false, message: 'Printer did not provide file data' });
            }
        } else {
            processFileListResult({ success: false, message: result.message });
        }
    } catch (error) {
        console.error('Error fetching print files:', error);
        processFileListResult({ success: false, message: 'Network error: Could not connect to printer' });
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
                    <h6 class="card-title mb-1">${file.name}</h6>
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
            <button class="btn btn-success btn-sm w-100 file-start-btn">
                <i class="bi bi-play-fill"></i> Start Print
            </button>
        </div>
    `;

    const startButton = cardDiv.querySelector('.file-start-btn');
    if (startButton) {
        startButton.addEventListener('click', (event) => {
            event.stopPropagation();
            startPrintFile(file.internal_name || file.name, file.name);
        });
    }

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
    const infoDiv = document.getElementById('selected-file-info');
    if (infoDiv) {
        infoDiv.style.display = 'none';
    }
}

// Start printing selected file
async function startSelectedPrint() {
    if (!selectedPrintFile) {
        showAlert('No file selected', 'warning');
        return;
    }

    const filename = selectedPrintFile.internal_name || selectedPrintFile.name;
    await startPrintFile(filename, selectedPrintFile.name);
}

// Start printing a specific file
async function startPrintFile(filename, displayName = null) {
    const visibleName = displayName || filename;

    if (!confirm(`Start printing "${visibleName}"?\n\nThis will begin the print job on the printer.`)) {
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
            showAlert(`Print started: ${visibleName}`, 'success');
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


// Helper functions
function formatDuration(seconds) {
    if (!seconds || seconds < 0) return '--';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

function hideAllFileStates() {
    const loading = document.getElementById('print-files-loading');
    const empty = document.getElementById('print-files-empty');
    const errorDiv = document.getElementById('print-files-error');
    const list = document.getElementById('print-files-list');

    if (loading) loading.style.display = 'none';
    if (empty) empty.style.display = 'none';
    if (errorDiv) errorDiv.style.display = 'none';
    if (list) list.style.display = 'none';
}

function showFileError(message) {
    hideAllFileStates();
    const errorDiv = document.getElementById('print-files-error');
    const errorMsg = document.getElementById('print-files-error-message');
    errorMsg.textContent = message;
    errorDiv.style.display = 'block';
}

function formatFileSize(bytes) {
    if (bytes === null || bytes === undefined) return 'Unknown';
    if (bytes === 0) return '0 B';
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