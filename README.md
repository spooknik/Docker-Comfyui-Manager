# ComfyUI Docker Manager

Automatically manage your ComfyUI Docker container based on demand. Saves power and resources by stopping the container when idle and automatically starting it when someone accesses it.

## Features

- **Auto-Stop**: Monitors ComfyUI's queue and stops the container after a configurable idle timeout
- **Wake-on-Access**: Automatically starts the container when someone tries to access ComfyUI
- **Web Dashboard**: Clean GUI showing container status, queue info, and configuration
- **Real-time Updates**: WebSocket-based live status updates
- **Configurable**: Adjust idle timeout, auto-start behavior, and more via the GUI
- **Docker-native**: Runs as a Docker container alongside your ComfyUI container

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- ComfyUI running in a Docker container (e.g., [YanWenKun/ComfyUI-Docker](https://github.com/YanWenKun/ComfyUI-Docker))
- Both containers on the same Docker network

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/Docker-Comfyui-Manager.git
   cd Docker-Comfyui-Manager
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` to match your ComfyUI setup:
   ```env
   # Name of your ComfyUI container
   COMFYUI_CONTAINER_NAME=comfyui

   # Idle timeout in minutes
   IDLE_TIMEOUT_MINUTES=30
   ```

4. Create the Docker network (if not already created):
   ```bash
   docker network create comfyui-network
   ```

5. Build and start the manager:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

6. Access the manager at `http://localhost:8080`

### Connecting to ComfyUI

Make sure your ComfyUI container is on the same Docker network. Update your ComfyUI docker-compose to include:

```yaml
services:
  comfyui:
    # ... your existing config
    networks:
      - comfyui-network

networks:
  comfyui-network:
    external: true
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `COMFYUI_CONTAINER_NAME` | `comfyui` | Docker container name to manage |
| `COMFYUI_HOST` | `comfyui` | Hostname for ComfyUI (usually same as container name) |
| `COMFYUI_PORT` | `8188` | ComfyUI web UI port |
| `IDLE_TIMEOUT_MINUTES` | `30` | Minutes before auto-stop |
| `POLL_INTERVAL_SECONDS` | `30` | How often to check queue status |
| `AUTO_START_ENABLED` | `true` | Enable wake-on-access |
| `STARTUP_TIMEOUT_SECONDS` | `120` | Max wait time for container start |
| `MANAGER_PORT` | `8080` | Manager web UI port |

All settings can also be changed via the web GUI.

## Usage

### Web Dashboard

Access the manager at `http://your-server:8080`:

- **Status Card**: Shows container state with start/stop buttons
- **Queue Status**: Displays running/pending jobs and idle timer
- **Settings**: Configure timeout, auto-start, and container name
- **Activity Log**: Recent events and state changes

### Accessing ComfyUI

When the container is running, click "Open ComfyUI" or go directly to `http://your-server:8080/comfyui`.

If the container is stopped and auto-start is enabled, it will automatically start when you access ComfyUI.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Host (TrueNAS)                    │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐ │
│  │  ComfyUI Manager    │    │     ComfyUI Container           │ │
│  │  (This Project)     │    │     (YanWenKun/ComfyUI-Docker)  │ │
│  │                     │    │                                 │ │
│  │  - FastAPI Backend  │───▶│  Port 8188                      │ │
│  │  - React Frontend   │    │  - Web UI                       │ │
│  │  - Docker SDK       │    │  - Queue API                    │ │
│  │                     │    │                                 │ │
│  │  Port 8080          │    │                                 │ │
│  └─────────────────────┘    └─────────────────────────────────┘ │
│           │                              │                      │
│           └──────────────────────────────┘                      │
│                    Docker Network                               │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Get container status, queue info, idle timer |
| POST | `/api/start` | Start the container |
| POST | `/api/stop` | Stop the container |
| GET | `/api/config` | Get current configuration |
| PUT | `/api/config` | Update configuration |
| GET | `/api/logs` | Get container logs |
| GET | `/api/activity` | Get activity log |
| WS | `/ws` | WebSocket for real-time updates |
| ANY | `/comfyui/*` | Reverse proxy to ComfyUI |

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on port 3000 and proxies API requests to the backend.

### Building

Build the combined Docker image:

```bash
docker build -t comfyui-manager .
```

## TrueNAS Deployment

1. Create a new Docker Compose application in TrueNAS
2. Use the contents of `docker-compose.prod.yml`
3. Add the environment variables from `.env.example`
4. Make sure to mount the Docker socket: `/var/run/docker.sock`
5. Ensure the manager is on the same network as ComfyUI

## Troubleshooting

### Container not found

- Verify the `COMFYUI_CONTAINER_NAME` matches your ComfyUI container name
- Check that both containers are on the same Docker network

### Cannot connect to ComfyUI

- Ensure `COMFYUI_HOST` matches your ComfyUI container name
- Verify port 8188 is correct for your setup
- Check that ComfyUI is actually running

### Docker socket permission denied

- The manager container needs access to the Docker socket
- On some systems, you may need to adjust socket permissions

## License

MIT License
