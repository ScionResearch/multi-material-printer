// Scion Multi-Material Printer Web Interface - JavaScript Utilities

// Global variables
let socket = null;
let connectionStatus = 'disconnected';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    initializeAlerts();
    updateConnectionIndicator();
});

// Socket.IO connection management
function initializeSocket() {
    socket = io();

    socket.on('connect', function() {
        connectionStatus = 'connected';
        updateConnectionIndicator();
        console.log('Connected to server');
    });

    socket.on('disconnect', function() {
        connectionStatus = 'disconnected';
        updateConnectionIndicator();
        console.log('Disconnected from server');
    });

    socket.on('connect_error', function(error) {
        connectionStatus = 'error';
        updateConnectionIndicator();
        console.error('Connection error:', error);
    });

    // Global event handlers
    socket.on('status_update', function(data) {
        // This will be overridden by page-specific handlers
        console.log('Status update:', data);
    });

    socket.on('system_alert', function(data) {
        showAlert(data.message, data.type || 'info');
    });
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
    formatDuration
};

// Initialize theme on load
loadSavedTheme();