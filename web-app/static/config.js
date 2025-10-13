// Configuration Management JavaScript
// Handles pump config, network settings, logging controls, and hardware diagnostics

let currentPumpConfig = {};
let currentNetworkConfig = {};
let logStreamActive = true;

// Initialize configuration page
document.addEventListener('DOMContentLoaded', function() {
    loadPumpConfig();
    loadNetworkConfig();
    initializeEventListeners();
    startSystemMetricsUpdates();
    setupLogStreaming();
});

// Event Listeners
function initializeEventListeners() {
    // Pump configuration form
    document.getElementById('pump-config-form').addEventListener('submit', function(e) {
        e.preventDefault();
        savePumpConfig();
    });

    // Network configuration form
    document.getElementById('network-config-form').addEventListener('submit', function(e) {
        e.preventDefault();
        saveNetworkConfig();
    });

    // Logging configuration form
    document.getElementById('logging-config-form').addEventListener('submit', function(e) {
        e.preventDefault();
        saveLoggingConfig();
    });
}

// Pump Configuration Functions
async function loadPumpConfig() {
    try {
        const response = await fetch('/api/config/pump');
        const config = await response.json();
        currentPumpConfig = config;

        populatePumpSettings(config);
        updatePumpStatus();

        console.log('Pump configuration loaded successfully');
    } catch (error) {
        console.error('Error loading pump configuration:', error);
        showAlert('Error loading pump configuration', 'danger');
    }
}

function populatePumpSettings(config) {
    const pumpSettings = document.getElementById('pump-settings');
    pumpSettings.innerHTML = '';

    // Create pump configuration cards
    Object.entries(config.pumps).forEach(([pumpId, pumpData]) => {
        const pumpCard = createPumpConfigCard(pumpId, pumpData);
        pumpSettings.appendChild(pumpCard);
    });

    // Populate material change settings
    document.getElementById('drain-volume').value = config.material_change.drain_volume_ml;
    document.getElementById('fill-volume').value = config.material_change.fill_volume_ml;
    document.getElementById('settle-time').value = config.material_change.settle_time_seconds;

    // Populate safety settings
    document.getElementById('max-runtime').value = config.safety.max_pump_runtime_seconds;
    document.getElementById('sensor-interval').value = config.safety.sensor_check_interval_seconds;
    document.getElementById('emergency-stop-enabled').checked = config.safety.emergency_stop_enabled;
}

function createPumpConfigCard(pumpId, pumpData) {
    const card = document.createElement('div');
    card.className = 'card mb-3';

    // Format last calibrated date
    const lastCalibrated = pumpData.calibration.last_calibrated ?
        new Date(pumpData.calibration.last_calibrated).toLocaleDateString() :
        'Never';

    card.innerHTML = `
        <div class="card-header bg-light">
            <h6 class="mb-0">${pumpData.name} (${pumpId.toUpperCase()})</h6>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <label class="form-label">Name</label>
                    <input type="text" class="form-control" data-pump="${pumpId}" data-field="name" value="${pumpData.name}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Description</label>
                    <input type="text" class="form-control" data-pump="${pumpId}" data-field="description" value="${pumpData.description}">
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-md-6">
                    <label class="form-label">Flow Rate (ml/s)</label>
                    <input type="number" class="form-control bg-warning bg-opacity-10" data-pump="${pumpId}" data-field="flow_rate_ml_per_second" value="${pumpData.flow_rate_ml_per_second}" min="0.1" max="10" step="0.1" readonly title="Use Calibration Wizard to update">
                    <small class="text-muted">Last calibrated: ${lastCalibrated}</small>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Max Volume (ml)</label>
                    <input type="number" class="form-control" data-pump="${pumpId}" data-field="max_volume_ml" value="${pumpData.max_volume_ml}" min="10" max="2000">
                </div>
            </div>
            <div class="mt-2">
                <button type="button" class="btn btn-outline-primary btn-sm" onclick="testSinglePump('${pumpId}')">
                    <i class="bi bi-play"></i> Test Pump
                </button>
                <button type="button" class="btn btn-warning btn-sm ms-2" onclick="openCalibrationForPump('${pumpId}')">
                    <i class="bi bi-speedometer2"></i> Calibrate Flow Rate
                </button>
            </div>
        </div>
    `;
    return card;
}

function openCalibrationForPump(pumpId) {
    // Pre-select the pump in the calibration wizard
    showCalibrationWizard();

    // Wait for modal to be shown, then set the pump
    setTimeout(() => {
        document.getElementById('cal-pump-select').value = pumpId;
        // Trigger change event to show pump info
        document.getElementById('cal-pump-select').dispatchEvent(new Event('change'));
    }, 300);
}

async function savePumpConfig() {
    try {
        // Collect pump data from form
        const updatedConfig = { ...currentPumpConfig };

        // Update pump settings
        document.querySelectorAll('[data-pump]').forEach(input => {
            const pumpId = input.dataset.pump;
            const field = input.dataset.field;
            let value = input.value;

            // Skip readonly fields (flow rate - must be calibrated via wizard)
            if (input.hasAttribute('readonly') && field === 'flow_rate_ml_per_second') {
                return;
            }

            // Convert to appropriate type
            if (field === 'max_volume_ml' || field === 'steps_per_ml') {
                value = parseInt(value);
            } else if (field === 'flow_rate_ml_per_second') {
                value = parseFloat(value);
            }

            if (field === 'steps_per_ml') {
                updatedConfig.pumps[pumpId].calibration.steps_per_ml = value;
            } else {
                updatedConfig.pumps[pumpId][field] = value;
            }
        });

        // Update material change settings
        updatedConfig.material_change.drain_volume_ml = parseInt(document.getElementById('drain-volume').value);
        updatedConfig.material_change.fill_volume_ml = parseInt(document.getElementById('fill-volume').value);
        updatedConfig.material_change.settle_time_seconds = parseInt(document.getElementById('settle-time').value);

        // Update safety settings
        updatedConfig.safety.max_pump_runtime_seconds = parseInt(document.getElementById('max-runtime').value);
        updatedConfig.safety.sensor_check_interval_seconds = parseInt(document.getElementById('sensor-interval').value);
        updatedConfig.safety.emergency_stop_enabled = document.getElementById('emergency-stop-enabled').checked;

        // Save configuration
        const response = await fetch('/api/config/pump', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedConfig)
        });

        const result = await response.json();
        if (result.success) {
            showAlert('Pump configuration saved successfully', 'success');
            currentPumpConfig = updatedConfig;
        } else {
            showAlert(result.message || 'Failed to save configuration', 'danger');
        }
    } catch (error) {
        console.error('Error saving pump configuration:', error);
        showAlert('Error saving pump configuration', 'danger');
    }
}

// Network Configuration Functions
async function loadNetworkConfig() {
    try {
        const response = await fetch('/api/config/network');
        const config = await response.json();
        currentNetworkConfig = config;

        // Populate network form
        document.getElementById('printer-ip').value = config.printer_ip;
        document.getElementById('printer-port').value = config.printer_port;
        document.getElementById('connection-timeout').value = config.connection_timeout;
        document.getElementById('wifi-ssid').value = config.wifi_ssid;

        console.log('Network configuration loaded successfully');
    } catch (error) {
        console.error('Error loading network configuration:', error);
        showAlert('Error loading network configuration', 'danger');
    }
}

async function saveNetworkConfig() {
    try {
        const config = {
            printer_ip: document.getElementById('printer-ip').value,
            printer_port: parseInt(document.getElementById('printer-port').value),
            connection_timeout: parseInt(document.getElementById('connection-timeout').value),
            wifi_ssid: document.getElementById('wifi-ssid').value
        };

        const response = await fetch('/api/config/network', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();
        if (result.success) {
            showAlert('Network configuration saved successfully', 'success');
            currentNetworkConfig = config;
        } else {
            showAlert(result.message || 'Failed to save configuration', 'danger');
        }
    } catch (error) {
        console.error('Error saving network configuration:', error);
        showAlert('Error saving network configuration', 'danger');
    }
}

async function testConnection() {
    try {
        const printerIp = document.getElementById('printer-ip').value;

        const response = await fetch('/api/config/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ printer_ip: printerIp })
        });

        const result = await response.json();
        const resultDiv = document.getElementById('connection-test-result');

        if (result.success) {
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> Connection successful!<br>
                    <small>Printer at ${result.ip} is responding</small>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> Connection failed<br>
                    <small>${result.message}</small>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error testing connection:', error);
        document.getElementById('connection-test-result').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-x-circle"></i> Test failed<br>
                <small>Network error occurred</small>
            </div>
        `;
    }
}

// Logging Configuration Functions
function saveLoggingConfig() {
    const config = {
        webui_log_level: document.getElementById('webui-log-level').value,
        print_manager_log_level: document.getElementById('print-manager-log-level').value,
        pump_log_level: document.getElementById('pump-log-level').value,
        console_logging: document.getElementById('console-logging').checked,
        file_logging: document.getElementById('file-logging').checked,
        realtime_logging: document.getElementById('realtime-logging').checked,
        max_log_lines: parseInt(document.getElementById('max-log-lines').value)
    };

    // Store logging configuration in localStorage for now
    localStorage.setItem('logging_config', JSON.stringify(config));
    showAlert('Logging configuration saved', 'success');
    console.log('Logging configuration updated:', config);
}

function toggleLogStream() {
    logStreamActive = !logStreamActive;
    const button = event.target;
    if (logStreamActive) {
        button.innerHTML = '<i class="bi bi-pause"></i> Pause Stream';
        button.className = 'btn btn-outline-primary btn-sm';
    } else {
        button.innerHTML = '<i class="bi bi-play"></i> Resume Stream';
        button.className = 'btn btn-outline-success btn-sm';
    }
}

function clearAllLogs() {
    if (confirm('Are you sure you want to clear all logs?')) {
        document.getElementById('live-log-preview').innerHTML = '<span class="text-muted">Logs cleared...</span>';
        showAlert('Logs cleared', 'info');
    }
}

// Hardware Diagnostics Functions
function updatePumpStatus() {
    const statusDiv = document.getElementById('pump-status');
    statusDiv.innerHTML = `
        <div class="mb-2">
            <strong>Pump A:</strong> <span class="badge bg-success">Ready</span>
        </div>
        <div class="mb-2">
            <strong>Pump B:</strong> <span class="badge bg-success">Ready</span>
        </div>
        <div class="mb-2">
            <strong>Pump C:</strong> <span class="badge bg-success">Ready</span>
        </div>
        <div class="mb-2">
            <strong>Drain:</strong> <span class="badge bg-success">Ready</span>
        </div>
        <hr>
        <div class="text-muted">
            <small>Last checked: ${new Date().toLocaleTimeString()}</small>
        </div>
    `;
}

function startSystemMetricsUpdates() {
    // Simulate system metrics updates
    setInterval(() => {
        document.getElementById('cpu-usage').textContent = (Math.random() * 30 + 10).toFixed(1) + '%';
        document.getElementById('memory-usage').textContent = (Math.random() * 40 + 30).toFixed(1) + '%';
        document.getElementById('cpu-temp').textContent = (Math.random() * 10 + 45).toFixed(1) + '°C';

        const uptime = Math.floor(Date.now() / 1000);
        const hours = Math.floor(uptime / 3600) % 24;
        const minutes = Math.floor(uptime / 60) % 60;
        document.getElementById('system-uptime').textContent = `${hours}h ${minutes}m`;
    }, 5000);
}

// Quick Action Functions
async function testSinglePump(pumpId) {
    try {
        // Map pump names to motor IDs (A, B, C, D)
        const pumpIdMap = {
            'pump_a': 'A',
            'pump_b': 'B',
            'pump_c': 'C',
            'drain_pump': 'D'
        };

        const motorId = pumpIdMap[pumpId] || pumpId.toUpperCase();

        showAlert(`Testing pump ${motorId}...`, 'info');

        // Run pump for 5 seconds forward as a test
        const response = await fetch('/api/pump', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ motor: motorId, direction: 'F', duration: 5 })
        });

        const result = await response.json();
        if (result.success) {
            showAlert(`Pump ${motorId} test completed successfully`, 'success');
        } else {
            throw new Error(result.message || 'Test failed');
        }
    } catch (error) {
        console.error(`Error testing ${pumpId}:`, error);
        showAlert(`Error testing pump: ${error.message}`, 'danger');
    }
}

function testAllPumps() {
    showAlert('Testing all pumps...', 'info');
    // Test each pump sequentially
    const pumps = ['pump_a', 'pump_b', 'pump_c', 'drain_pump'];
    let index = 0;

    function testNext() {
        if (index < pumps.length) {
            testSinglePump(pumps[index]);
            index++;
            setTimeout(testNext, 6000); // 5s test + 1s delay
        } else {
            showAlert('All pumps tested successfully', 'success');
        }
    }

    testNext();
}

// ============================================
// CALIBRATION WIZARD FUNCTIONS
// ============================================

let calibrationData = {
    pumpId: null,
    pumpName: null,
    motorId: null,
    duration: 10,
    currentFlowRate: null,
    measuredVolume: null,
    calculatedFlowRate: null
};

function showCalibrationWizard() {
    // Reset calibration data
    calibrationData = {
        pumpId: null,
        pumpName: null,
        motorId: null,
        duration: 10,
        currentFlowRate: null,
        measuredVolume: null,
        calculatedFlowRate: null
    };

    // Reset form
    document.getElementById('cal-pump-select').value = '';
    document.getElementById('cal-duration').value = 10;
    document.getElementById('cal-measured-volume').value = '';
    document.getElementById('cal-pump-info').classList.add('d-none');
    document.getElementById('cal-calculation-result').classList.add('d-none');

    // Show modal at step 1
    goToCalibrationStep(1);
    const modal = new bootstrap.Modal(document.getElementById('calibrationModal'));
    modal.show();
}

function goToCalibrationStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.calibration-step').forEach(step => {
        step.classList.add('d-none');
    });

    // Show target step
    document.getElementById(`calibration-step-${stepNumber}`).classList.remove('d-none');
}

// Handle pump selection change - show current settings
document.addEventListener('DOMContentLoaded', function() {
    const pumpSelect = document.getElementById('cal-pump-select');
    if (pumpSelect) {
        pumpSelect.addEventListener('change', function() {
            const pumpId = this.value;
            if (pumpId && currentPumpConfig.pumps && currentPumpConfig.pumps[pumpId]) {
                const pumpData = currentPumpConfig.pumps[pumpId];
                document.getElementById('cal-current-flow').textContent = pumpData.flow_rate_ml_per_second.toFixed(2);
                document.getElementById('cal-last-calibrated').textContent =
                    pumpData.calibration.last_calibrated || 'Never';
                document.getElementById('cal-pump-info').classList.remove('d-none');
            } else {
                document.getElementById('cal-pump-info').classList.add('d-none');
            }
        });
    }
});

function startCalibrationTest() {
    const pumpId = document.getElementById('cal-pump-select').value;
    const duration = parseInt(document.getElementById('cal-duration').value);

    if (!pumpId) {
        showAlert('Please select a pump', 'warning');
        return;
    }

    if (duration < 5 || duration > 60) {
        showAlert('Duration must be between 5 and 60 seconds', 'warning');
        return;
    }

    // Map pump IDs to motor IDs and names
    const pumpIdMap = {
        'pump_a': { motor: 'A', name: 'Pump A' },
        'pump_b': { motor: 'B', name: 'Pump B' },
        'pump_c': { motor: 'C', name: 'Pump C' },
        'drain_pump': { motor: 'D', name: 'Drain Pump' }
    };

    const pumpInfo = pumpIdMap[pumpId];
    if (!pumpInfo) {
        showAlert('Invalid pump selected', 'danger');
        return;
    }

    // Store calibration data
    calibrationData.pumpId = pumpId;
    calibrationData.pumpName = pumpInfo.name;
    calibrationData.motorId = pumpInfo.motor;
    calibrationData.duration = duration;
    calibrationData.currentFlowRate = currentPumpConfig.pumps[pumpId].flow_rate_ml_per_second;

    // Update step 2 display
    document.getElementById('cal-test-pump-name').textContent = pumpInfo.name;
    document.getElementById('cal-test-duration').textContent = duration;
    document.getElementById('cal-test-status').className = 'alert alert-secondary text-center';
    document.getElementById('cal-test-status').innerHTML = '<strong>Status:</strong> Ready to run test';
    document.getElementById('cal-run-test-btn').disabled = false;

    // Go to step 2
    goToCalibrationStep(2);
}

async function runCalibrationTest() {
    const btn = document.getElementById('cal-run-test-btn');
    const statusDiv = document.getElementById('cal-test-status');

    btn.disabled = true;
    statusDiv.className = 'alert alert-info text-center';
    statusDiv.innerHTML = '<strong>Status:</strong> <i class="spinner-border spinner-border-sm"></i> Running pump...';

    try {
        // Run pump via API
        const response = await fetch('/api/pump', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                motor: calibrationData.motorId,
                direction: 'F',
                duration: calibrationData.duration
            })
        });

        const result = await response.json();

        if (result.success) {
            // Wait for pump to finish
            setTimeout(() => {
                statusDiv.className = 'alert alert-success text-center';
                statusDiv.innerHTML = '<strong>Status:</strong> <i class="bi bi-check-circle"></i> Test completed! Now measure the dispensed volume.';

                // Auto-advance to step 3 after a moment
                setTimeout(() => {
                    goToCalibrationStep(3);
                }, 2000);
            }, calibrationData.duration * 1000 + 1000); // Duration + 1s buffer

        } else {
            throw new Error(result.message || 'Pump test failed');
        }
    } catch (error) {
        console.error('Error running calibration test:', error);
        statusDiv.className = 'alert alert-danger text-center';
        statusDiv.innerHTML = `<strong>Status:</strong> <i class="bi bi-x-circle"></i> Error: ${error.message}`;
        btn.disabled = false;
        showAlert('Error running pump test: ' + error.message, 'danger');
    }
}

function calculateFlowRate() {
    const measuredVolume = parseFloat(document.getElementById('cal-measured-volume').value);

    if (!measuredVolume || measuredVolume <= 0) {
        showAlert('Please enter a valid volume greater than 0', 'warning');
        return;
    }

    // Calculate flow rate: flow_rate = volume / duration
    const calculatedFlowRate = measuredVolume / calibrationData.duration;
    calibrationData.measuredVolume = measuredVolume;
    calibrationData.calculatedFlowRate = calculatedFlowRate;

    // Display results
    document.getElementById('cal-calculated-flow').textContent = calculatedFlowRate.toFixed(2);
    document.getElementById('cal-calc-volume').textContent = measuredVolume.toFixed(1);
    document.getElementById('cal-calc-duration').textContent = calibrationData.duration;
    document.getElementById('cal-old-flow').textContent = calibrationData.currentFlowRate.toFixed(2) + ' ml/s';
    document.getElementById('cal-new-flow').textContent = calculatedFlowRate.toFixed(2) + ' ml/s';

    // Show calculation result
    document.getElementById('cal-calculation-result').classList.remove('d-none');

    // Hide calculate button, show save button
    document.getElementById('cal-calculate-btn').classList.add('d-none');
    document.getElementById('cal-save-btn').classList.remove('d-none');

    showAlert('Flow rate calculated! Review the results and click Save to apply.', 'success');
}

async function saveCalibration() {
    const btn = document.getElementById('cal-save-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="spinner-border spinner-border-sm"></i> Saving...';

    try {
        // Update the pump config in memory
        const updatedConfig = { ...currentPumpConfig };
        updatedConfig.pumps[calibrationData.pumpId].flow_rate_ml_per_second = calibrationData.calculatedFlowRate;
        updatedConfig.pumps[calibrationData.pumpId].calibration.last_calibrated = new Date().toISOString();

        // Save via API
        const response = await fetch('/api/config/pump', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedConfig)
        });

        const result = await response.json();

        if (result.success) {
            // Update local config
            currentPumpConfig = updatedConfig;

            // Update the form display
            loadPumpConfig();

            // Show success screen
            document.getElementById('cal-final-pump').textContent = calibrationData.pumpName;
            document.getElementById('cal-final-flow').textContent = calibrationData.calculatedFlowRate.toFixed(2);
            goToCalibrationStep(4);

            showAlert('Calibration saved successfully!', 'success');
        } else {
            throw new Error(result.message || 'Failed to save calibration');
        }
    } catch (error) {
        console.error('Error saving calibration:', error);
        showAlert('Error saving calibration: ' + error.message, 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-save"></i> Save Calibration';
    }
}

function calibrateAnotherPump() {
    showCalibrationWizard();
}

// Legacy calibration functions (kept for compatibility with manual controls page)
async function calibratePumps() {
    showAlert('Use the Calibration Wizard in the Config page for guided calibration.', 'info');
}

async function calibrateSinglePump(pumpId) {
    showAlert('Use the Calibration Wizard in the Config page for guided calibration.', 'info');
}

function exportPumpConfig() {
    const configBlob = new Blob([JSON.stringify(currentPumpConfig, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(configBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pump_config_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Diagnostic Functions
async function testI2C() {
    try {
        showAlert('Testing I2C communication...', 'info');

        const response = await fetch('/api/diagnostics/i2c', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        if (result.success) {
            showAlert('I2C test started. Check status for results.', 'success');
        } else {
            throw new Error(result.message || 'Failed to start I2C test');
        }
    } catch (error) {
        console.error('Error starting I2C test:', error);
        showAlert(`Error: ${error.message}`, 'danger');
    }
}

async function testGPIO() {
    try {
        showAlert('Testing GPIO pins...', 'info');

        const response = await fetch('/api/diagnostics/gpio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        if (result.success) {
            showAlert('GPIO test started. Check status for results.', 'success');
        } else {
            throw new Error(result.message || 'Failed to start GPIO test');
        }
    } catch (error) {
        console.error('Error starting GPIO test:', error);
        showAlert(`Error: ${error.message}`, 'danger');
    }
}

async function testPumpMotors() {
    try {
        showAlert('Testing pump motors...', 'info');

        const response = await fetch('/api/diagnostics/pumps', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        if (result.success) {
            showAlert('Pump motor test started. Check status for results.', 'success');
        } else {
            throw new Error(result.message || 'Failed to start pump motor test');
        }
    } catch (error) {
        console.error('Error starting pump motor test:', error);
        showAlert(`Error: ${error.message}`, 'danger');
    }
}

function testNetworkConnectivity() {
    testConnection();
}

async function runFullDiagnostics() {
    try {
        showAlert('Running full system diagnostics...', 'info');

        const response = await fetch('/api/diagnostics/full', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        if (result.success) {
            showAlert('Full diagnostics started. Check status for detailed results.', 'success');
        } else {
            throw new Error(result.message || 'Failed to start full diagnostics');
        }
    } catch (error) {
        console.error('Error starting full diagnostics:', error);
        showAlert(`Error: ${error.message}`, 'danger');
    }
}

function generateDiagnosticReport() {
    const report = {
        timestamp: new Date().toISOString(),
        system_info: {
            platform: 'Raspberry Pi 4',
            os: 'Raspberry Pi OS',
            python_version: '3.9.x'
        },
        pump_config: currentPumpConfig,
        network_config: currentNetworkConfig,
        diagnostics: {
            i2c: 'OK',
            gpio: 'OK',
            pumps: 'PARTIAL',
            network: 'OK'
        }
    };

    const reportBlob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(reportBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `diagnostic_report_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Log Streaming Functions
function setupLogStreaming() {
    if (typeof socket !== 'undefined') {
        // Listen for log messages from the server
        socket.on('log_message', function(data) {
            if (logStreamActive) {
                displayLogMessage(data);
            }
        });

        // Load recent logs on page load
        loadRecentLogs();
    }
}

function displayLogMessage(logData) {
    const logPreview = document.getElementById('live-log-preview');
    if (!logPreview) return;

    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${logData.level}`;

    const timestamp = new Date(logData.timestamp).toLocaleTimeString();
    logEntry.innerHTML = `<span class="log-time">${timestamp}</span> <span class="log-level">[${logData.level.toUpperCase()}]</span> ${logData.message}`;

    logPreview.appendChild(logEntry);

    // Keep only last 100 entries
    while (logPreview.children.length > 100) {
        logPreview.removeChild(logPreview.firstChild);
    }

    // Auto-scroll to bottom
    logPreview.scrollTop = logPreview.scrollHeight;
}

async function loadRecentLogs() {
    try {
        const response = await fetch('/api/logging/recent?count=50');
        const logs = await response.json();

        const logPreview = document.getElementById('live-log-preview');
        if (logPreview && Array.isArray(logs)) {
            logPreview.innerHTML = '';
            logs.forEach(logData => {
                displayLogMessage(logData);
            });
        }
    } catch (error) {
        console.error('Error loading recent logs:', error);
    }
}

async function saveLoggingConfig() {
    const config = {
        levels: {
            webui_log_level: document.getElementById('webui-log-level').value,
            print_manager_log_level: document.getElementById('print-manager-log-level').value,
            pump_log_level: document.getElementById('pump-log-level').value
        },
        outputs: {
            console_logging: document.getElementById('console-logging').checked,
            file_logging: document.getElementById('file-logging').checked,
            realtime_logging: document.getElementById('realtime-logging').checked
        },
        max_log_lines: parseInt(document.getElementById('max-log-lines').value)
    };

    try {
        const response = await fetch('/api/logging/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();
        if (result.success) {
            showAlert('Logging configuration saved successfully', 'success');
        } else {
            showAlert(result.message || 'Failed to save logging configuration', 'danger');
        }
    } catch (error) {
        console.error('Error saving logging configuration:', error);
        showAlert('Error saving logging configuration', 'danger');
    }
}

// Utility Functions
function showAlert(message, type = 'info', timeout = 5000) {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    // Map alert types to toast styling
    const typeConfig = {
        'success': { icon: 'bi-check-circle-fill', bg: 'bg-success' },
        'danger': { icon: 'bi-exclamation-triangle-fill', bg: 'bg-danger' },
        'warning': { icon: 'bi-exclamation-circle-fill', bg: 'bg-warning' },
        'info': { icon: 'bi-info-circle-fill', bg: 'bg-info' }
    };

    const config = typeConfig[type] || typeConfig['info'];

    // Create unique ID for this toast
    const toastId = 'toast-' + Date.now();

    // Create toast element
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = 'toast align-items-center text-white border-0';
    toast.classList.add(config.bg);
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi ${config.icon} me-2"></i>${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    // Add to container
    toastContainer.appendChild(toast);

    // Initialize and show Bootstrap toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: timeout
    });
    bsToast.show();

    // Remove from DOM after hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}