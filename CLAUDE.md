# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ComfyUI Manager is a lightweight Flask-based proxy application that sits in front of ComfyUI and automatically starts/stops it based on user activity to save GPU power. The architecture consists of:

- **Flask proxy server** (`app.py`) - Handles web UI and proxies all requests to ComfyUI
- **Process manager** (`comfyui_manager.py`) - Controls ComfyUI lifecycle (start/stop/monitor)
- **Auto-start/stop logic** - Starts ComfyUI on first request, stops after configurable idle timeout

The manager runs on port 8188 (external) and ComfyUI runs internally on 127.0.0.1:8189, not directly accessible from outside.

## Core Architecture

### Request Flow
1. User requests come to manager (port 8188)
2. Manager checks if ComfyUI is running
3. If not running, auto-starts ComfyUI and waits for it to be responsive
4. Manager proxies the request to ComfyUI (127.0.0.1:8189)
5. Any request resets the idle timer
6. Background thread monitors idle time; stops ComfyUI after timeout

### Key Components

**`ComfyUIManager` class (comfyui_manager.py)**
- Manages subprocess lifecycle using `subprocess.Popen`
- Uses process groups (POSIX) or direct termination (Windows) for clean shutdowns
- Background idle checker thread monitors activity and triggers shutdown
- `is_responsive` property checks `/system_stats` endpoint to verify ComfyUI is ready
- Thread-safe with locks for concurrent access

**Flask app (app.py)**
- `/manager` - Web UI for manual control
- `/manager/status`, `/manager/start`, `/manager/stop` - API endpoints
- `/` - Root redirects to manager UI or ComfyUI based on state
- `/comfyui/<path>` - Explicit ComfyUI proxy route
- `/<path>` - Catch-all proxy for all other paths (except manager routes)
- `proxy_request()` - Core proxy logic that streams responses

### Process Management

ComfyUI startup:
1. `start_comfyui()` spawns subprocess with configured command
2. Waits up to 120 seconds for `/system_stats` to return 200
3. If responsive, starts idle checker thread
4. If fails, kills process and returns error

ComfyUI shutdown:
1. Sends SIGTERM to process group (Unix) or terminate (Windows)
2. Waits 10 seconds for graceful shutdown
3. Forces SIGKILL if still running
4. Stops idle checker thread

## Docker Deployment

Two Dockerfile options:

1. **Dockerfile.managed** - Extends `yanwenkun/comfyui-boot:latest`
   - Adds manager dependencies on top of existing ComfyUI image
   - Manager runs as entrypoint, controls ComfyUI as subprocess
   - Recommended for production use

2. **Dockerfile** - Standalone Python image
   - Requires ComfyUI to be installed separately or mounted
   - Used for development/testing manager in isolation

## Development Commands

### Local Development (without Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Run directly (development server)
python app.py

# Run with gunicorn (production-like)
gunicorn --bind 0.0.0.0:8188 --workers 1 --threads 4 --timeout 300 app:app
```

### Docker Development

```bash
# Build managed image
docker build -f Dockerfile.managed -t comfyui-managed .

# Run with docker-compose (edit docker-compose.yml volume paths first)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Testing Configuration

Environment variables can be set in `config.env` (copy from `config.env.example`) or passed directly:

```bash
# Test with shorter timeout
IDLE_TIMEOUT_SECONDS=60 python app.py

# Test with different ComfyUI command
COMFYUI_START_CMD="python /custom/path/main.py" python app.py
```

## Configuration

All configuration via environment variables (see config.env.example):

- `COMFYUI_HOST` / `COMFYUI_PORT` - Internal ComfyUI address (default: 127.0.0.1:8189)
- `COMFYUI_START_CMD` - Command to start ComfyUI subprocess
- `MANAGER_PORT` - External port manager listens on (default: 8188)
- `IDLE_TIMEOUT_SECONDS` - Inactivity time before auto-stop (default: 300)
- `IDLE_CHECK_INTERVAL` - How often idle checker runs (default: 30)

## Important Implementation Details

### Proxy Behavior
- Streams responses using `resp.iter_content()` to handle large generations
- 300 second timeout for long-running generation requests
- Strips hop-by-hop headers (host, connection, transfer-encoding, etc.)
- Preserves cookies and query strings
- Returns 503 if ComfyUI won't start or isn't responsive

### Thread Safety
- `ComfyUIManager` uses `threading.Lock` for state changes
- Idle checker runs as daemon thread
- `_stop_idle_checker` event signals thread to stop

### Activity Tracking
- `record_activity()` updates `last_activity` timestamp
- Called on every proxied request
- Idle time = current time - last activity
- When idle time >= timeout, shutdown triggers

### Startup Wait Logic
Both proxy routes wait up to 30 seconds for ComfyUI to become responsive after auto-start. This prevents 503 errors if user requests arrive during startup window (ComfyUI takes time to load models).

## Windows vs Unix Differences

Process termination differs by platform:
- **Unix/Linux**: Uses `os.setsid()` to create process group, kills with `os.killpg()` to ensure child processes die
- **Windows**: Uses `process.terminate()` and `process.kill()` directly (no process groups)

## Testing the Manager

1. Access manager UI at `http://localhost:8188/manager`
2. Start ComfyUI manually or access root - should auto-start
3. Verify ComfyUI loads (check status endpoint)
4. Wait for idle timeout - should auto-stop
5. Access again - should auto-start again

Check logs for process lifecycle events (starting, responsive, idle timeout, stopping).
