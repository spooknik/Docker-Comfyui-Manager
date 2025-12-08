"""
ComfyUI Manager - Flask Application
A lightweight proxy that auto-starts/stops ComfyUI based on user activity.
"""

import os
import logging
from flask import Flask, request, Response, render_template_string, jsonify
from dotenv import load_dotenv
import requests
from comfyui_manager import ComfyUIManager

# Load environment variables
load_dotenv("config.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Configuration
COMFYUI_HOST = os.getenv("COMFYUI_HOST", "127.0.0.1")
COMFYUI_PORT = int(os.getenv("COMFYUI_PORT", "8189"))
COMFYUI_START_CMD = os.getenv(
    "COMFYUI_START_CMD",
    "python /root/ComfyUI/main.py --listen 127.0.0.1 --port 8189"
)
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT_SECONDS", "300"))
IDLE_CHECK_INTERVAL = int(os.getenv("IDLE_CHECK_INTERVAL", "30"))

# Initialize Flask app
app = Flask(__name__)

# Initialize ComfyUI manager
manager = ComfyUIManager(
    comfyui_host=COMFYUI_HOST,
    comfyui_port=COMFYUI_PORT,
    start_cmd=COMFYUI_START_CMD,
    idle_timeout=IDLE_TIMEOUT,
    check_interval=IDLE_CHECK_INTERVAL,
)

# HTML template for the manager frontend
MANAGER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ComfyUI Manager</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            color: #e0e0e0;
        }
        .container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            color: #fff;
            font-size: 28px;
        }
        .status-card {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .status-row:last-child {
            border-bottom: none;
        }
        .status-label {
            color: #aaa;
            font-size: 14px;
        }
        .status-value {
            font-weight: 600;
            font-size: 14px;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        .status-running {
            background: #4caf50;
            box-shadow: 0 0 10px #4caf50;
        }
        .status-stopped {
            background: #f44336;
            box-shadow: 0 0 10px #f44336;
        }
        .status-starting {
            background: #ff9800;
            box-shadow: 0 0 10px #ff9800;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .buttons {
            display: flex;
            gap: 15px;
            margin-top: 25px;
        }
        button {
            flex: 1;
            padding: 15px 25px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .btn-start {
            background: linear-gradient(135deg, #4caf50, #45a049);
            color: white;
        }
        .btn-start:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(76, 175, 80, 0.4);
        }
        .btn-stop {
            background: linear-gradient(135deg, #f44336, #d32f2f);
            color: white;
        }
        .btn-stop:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(244, 67, 54, 0.4);
        }
        .btn-open {
            background: linear-gradient(135deg, #2196f3, #1976d2);
            color: white;
        }
        .btn-open:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(33, 150, 243, 0.4);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 15px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4caf50, #ff9800, #f44336);
            transition: width 0.5s ease;
        }
        .idle-info {
            text-align: center;
            margin-top: 10px;
            font-size: 12px;
            color: #888;
        }
        .message {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            font-size: 14px;
        }
        .message.info {
            background: rgba(33, 150, 243, 0.2);
            border: 1px solid rgba(33, 150, 243, 0.3);
        }
        .message.error {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid rgba(244, 67, 54, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>ComfyUI Manager</h1>

        <div id="message" class="message" style="display: none;"></div>

        <div class="status-card">
            <div class="status-row">
                <span class="status-label">Status</span>
                <span class="status-value" id="status">
                    <span class="status-indicator status-stopped"></span>
                    Checking...
                </span>
            </div>
            <div class="status-row">
                <span class="status-label">Idle Time</span>
                <span class="status-value" id="idle-time">-</span>
            </div>
            <div class="status-row">
                <span class="status-label">Auto-shutdown in</span>
                <span class="status-value" id="shutdown-time">-</span>
            </div>
        </div>

        <div class="progress-bar" id="progress-container" style="display: none;">
            <div class="progress-fill" id="progress-fill" style="width: 100%;"></div>
        </div>
        <div class="idle-info" id="idle-info" style="display: none;">
            Activity resets the idle timer
        </div>

        <div class="buttons">
            <button class="btn-start" id="btn-start" onclick="startComfyUI()">Start</button>
            <button class="btn-stop" id="btn-stop" onclick="stopComfyUI()">Stop</button>
            <button class="btn-open" id="btn-open" onclick="openComfyUI()">Open UI</button>
        </div>
    </div>

    <script>
        let statusInterval;

        function formatTime(seconds) {
            if (seconds === null || seconds === undefined) return '-';
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            if (mins > 0) {
                return `${mins}m ${secs}s`;
            }
            return `${secs}s`;
        }

        function updateStatus() {
            fetch('/manager/status')
                .then(response => response.json())
                .then(data => {
                    const statusEl = document.getElementById('status');
                    const idleTimeEl = document.getElementById('idle-time');
                    const shutdownTimeEl = document.getElementById('shutdown-time');
                    const progressContainer = document.getElementById('progress-container');
                    const progressFill = document.getElementById('progress-fill');
                    const idleInfo = document.getElementById('idle-info');
                    const btnStart = document.getElementById('btn-start');
                    const btnStop = document.getElementById('btn-stop');
                    const btnOpen = document.getElementById('btn-open');

                    if (data.comfyui_starting) {
                        statusEl.innerHTML = '<span class="status-indicator status-starting"></span>Starting...';
                        btnStart.disabled = true;
                        btnStop.disabled = true;
                        btnOpen.disabled = true;
                        progressContainer.style.display = 'none';
                        idleInfo.style.display = 'none';
                    } else if (data.comfyui_running && data.comfyui_responsive) {
                        statusEl.innerHTML = '<span class="status-indicator status-running"></span>Running';
                        btnStart.disabled = true;
                        btnStop.disabled = false;
                        btnOpen.disabled = false;
                        progressContainer.style.display = 'block';
                        idleInfo.style.display = 'block';

                        // Update progress bar
                        const progress = (data.time_until_shutdown / data.idle_timeout) * 100;
                        progressFill.style.width = progress + '%';
                    } else if (data.comfyui_running) {
                        statusEl.innerHTML = '<span class="status-indicator status-starting"></span>Starting...';
                        btnStart.disabled = true;
                        btnStop.disabled = false;
                        btnOpen.disabled = true;
                        progressContainer.style.display = 'none';
                        idleInfo.style.display = 'none';
                    } else {
                        statusEl.innerHTML = '<span class="status-indicator status-stopped"></span>Stopped';
                        btnStart.disabled = false;
                        btnStop.disabled = true;
                        btnOpen.disabled = true;
                        progressContainer.style.display = 'none';
                        idleInfo.style.display = 'none';
                    }

                    idleTimeEl.textContent = formatTime(data.seconds_since_activity);
                    shutdownTimeEl.textContent = data.time_until_shutdown !== null
                        ? formatTime(data.time_until_shutdown)
                        : '-';
                })
                .catch(err => {
                    console.error('Failed to fetch status:', err);
                });
        }

        function showMessage(text, type) {
            const msgEl = document.getElementById('message');
            msgEl.textContent = text;
            msgEl.className = 'message ' + type;
            msgEl.style.display = 'block';
            setTimeout(() => {
                msgEl.style.display = 'none';
            }, 5000);
        }

        function startComfyUI() {
            document.getElementById('btn-start').disabled = true;
            showMessage('Starting ComfyUI... This may take a minute.', 'info');

            fetch('/manager/start', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showMessage('ComfyUI started successfully!', 'info');
                    } else {
                        showMessage('Failed to start ComfyUI: ' + (data.error || 'Unknown error'), 'error');
                    }
                    updateStatus();
                })
                .catch(err => {
                    showMessage('Failed to start ComfyUI', 'error');
                    updateStatus();
                });
        }

        function stopComfyUI() {
            document.getElementById('btn-stop').disabled = true;

            fetch('/manager/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showMessage('ComfyUI stopped', 'info');
                    }
                    updateStatus();
                })
                .catch(err => {
                    showMessage('Failed to stop ComfyUI', 'error');
                    updateStatus();
                });
        }

        function openComfyUI() {
            // Record activity when opening
            fetch('/manager/activity', { method: 'POST' });
            window.open('/comfyui/', '_blank');
        }

        // Initial status check and start polling
        updateStatus();
        statusInterval = setInterval(updateStatus, 2000);
    </script>
</body>
</html>
"""

# Paths that shouldn't trigger auto-start
MANAGER_PATHS = ['/manager', '/manager/', '/manager/status', '/manager/start', '/manager/stop', '/manager/activity']


@app.route('/manager')
@app.route('/manager/')
def manager_page():
    """Serve the manager frontend."""
    return render_template_string(MANAGER_HTML)


@app.route('/manager/status')
def manager_status():
    """Get current status."""
    return jsonify(manager.get_status())


@app.route('/manager/start', methods=['POST'])
def manager_start():
    """Manually start ComfyUI."""
    success = manager.start_comfyui()
    return jsonify({"success": success})


@app.route('/manager/stop', methods=['POST'])
def manager_stop():
    """Manually stop ComfyUI."""
    manager.stop_comfyui()
    return jsonify({"success": True})


@app.route('/manager/activity', methods=['POST'])
def manager_activity():
    """Record user activity."""
    manager.record_activity()
    return jsonify({"success": True})


@app.route('/')
def index():
    """Redirect root to manager or ComfyUI based on status."""
    if manager.is_running and manager.is_responsive:
        manager.record_activity()
        return proxy_request('')
    return render_template_string(MANAGER_HTML)


@app.route('/comfyui/')
@app.route('/comfyui/<path:path>')
def comfyui_proxy(path=''):
    """Proxy requests to ComfyUI with auto-start."""
    # Auto-start ComfyUI if not running
    if not manager.is_running:
        logger.info("ComfyUI not running, auto-starting...")
        if not manager.start_comfyui():
            return Response(
                "Failed to start ComfyUI. Please try again or check the logs.",
                status=503
            )

    # Wait for it to be responsive
    if not manager.is_responsive:
        import time
        for _ in range(30):
            if manager.is_responsive:
                break
            time.sleep(1)
        else:
            return Response("ComfyUI is starting, please wait and refresh...", status=503)

    # Record activity and proxy
    manager.record_activity()
    return proxy_request(path)


def proxy_request(path):
    """Proxy a request to ComfyUI."""
    # Build target URL
    target_url = f"{manager.comfyui_url}/{path}"
    if request.query_string:
        target_url += f"?{request.query_string.decode()}"

    # Get headers (excluding hop-by-hop)
    excluded_headers = {'host', 'connection', 'keep-alive', 'transfer-encoding'}
    headers = {
        key: value for key, value in request.headers
        if key.lower() not in excluded_headers
    }

    try:
        # Make the proxied request
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            stream=True,
            timeout=300,  # Long timeout for generation requests
        )

        # Build response headers
        response_headers = {}
        excluded_response = {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}
        for key, value in resp.headers.items():
            if key.lower() not in excluded_response:
                response_headers[key] = value

        return Response(
            resp.iter_content(chunk_size=8192),
            status=resp.status_code,
            headers=response_headers,
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Proxy error: {e}")
        return Response(f"Error connecting to ComfyUI: {e}", status=502)


# Catch-all route for all other paths (direct proxy to ComfyUI)
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def catch_all(path):
    """Catch-all route that proxies to ComfyUI."""
    # Skip manager paths
    if path.startswith('manager'):
        return Response("Not found", status=404)

    # Auto-start ComfyUI if not running
    if not manager.is_running:
        logger.info("ComfyUI not running, auto-starting...")
        if not manager.start_comfyui():
            return Response(
                "Failed to start ComfyUI. Please try again or check the logs.",
                status=503
            )

    # Wait for it to be responsive
    if not manager.is_responsive:
        import time
        for _ in range(30):
            if manager.is_responsive:
                break
            time.sleep(1)
        else:
            return Response("ComfyUI is starting, please wait and refresh...", status=503)

    # Record activity and proxy
    manager.record_activity()
    return proxy_request(path)


if __name__ == '__main__':
    port = int(os.getenv("MANAGER_PORT", "80"))
    logger.info(f"Starting ComfyUI Manager on port {port}")
    logger.info(f"ComfyUI target: {manager.comfyui_url}")
    logger.info(f"Idle timeout: {IDLE_TIMEOUT}s")
    app.run(host='0.0.0.0', port=port, debug=False)
