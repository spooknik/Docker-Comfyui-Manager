# ComfyUI Docker Manager

Automatically manage your ComfyUI Docker container based on demand. Saves power and resources by stopping the container when idle and automatically starting it when someone accesses it.

## Features

- **Auto-Stop**: Monitors ComfyUI's queue and stops the container after a configurable idle timeout
- **Wake-on-Access**: Automatically starts the container when someone tries to access ComfyUI
- **Web Dashboard**: Clean GUI showing container status, queue info, and configuration
- **Real-time Updates**: WebSocket-based live status updates
- **Configurable**: Adjust idle timeout, auto-start behavior, and more via the GUI
- **Docker-native**: Runs as a Docker container alongside your ComfyUI container

## Quick Start - Docker Hub

The easiest way to run the manager:

```bash
docker run -d \
  --name comfyui-manager \
  -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e COMFYUI_CONTAINER_NAME=your-comfyui-container-name \
  -e COMFYUI_HOST=your-comfyui-container-name \
  yourusername/comfyui-manager:latest
```

Replace `your-comfyui-container-name` with your actual ComfyUI container name.

## TrueNAS Installation

### Via TrueNAS Apps UI

1. Go to **Apps** > **Discover Apps** > **Custom App**
2. Configure the app:
   - **Application Name**: `comfyui-manager`
   - **Image Repository**: `yourusername/comfyui-manager`
   - **Image Tag**: `latest`
3. **Port Forwarding**:
   - Container Port: `8080` → Host Port: `8080`
4. **Environment Variables**:
   | Name | Value |
   |------|-------|
   | `COMFYUI_CONTAINER_NAME` | Your ComfyUI container name (find with `docker ps`) |
   | `COMFYUI_HOST` | Same as container name |
   | `IDLE_TIMEOUT_MINUTES` | `30` (or your preference) |
5. **Storage**:
   - Add Host Path: `/var/run/docker.sock` → `/var/run/docker.sock`
   - (Optional) Add volume for `/app/data` to persist config
6. Click **Install**

### Finding Your ComfyUI Container Name

SSH into TrueNAS and run:
```bash
docker ps | grep -i comfy
```
The first column is the container ID, the last column is the **container name**.

### Network Configuration

Both containers must be able to communicate. In TrueNAS, apps typically share the default network automatically. If not:

1. Find your ComfyUI container's network:
   ```bash
   docker inspect your-comfyui-container | grep -A 5 "Networks"
   ```

2. When setting up the manager, use the same network or use the container's IP address for `COMFYUI_HOST`.

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

All settings can also be changed via the web GUI.

## Usage

### Web Dashboard

Access the manager at `http://your-truenas-ip:8080`:

- **Status Card**: Shows container state with start/stop buttons
- **Queue Status**: Displays running/pending jobs and idle timer
- **Settings**: Configure timeout, auto-start, and container name
- **Activity Log**: Recent events and state changes

### Accessing ComfyUI

When the container is running, click "Open ComfyUI" or go directly to `http://your-truenas-ip:8080/comfyui`.

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

## Building from Source

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)

### Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Build Docker Image

```bash
docker build -t comfyui-manager .
```

### Push to Docker Hub

```bash
docker tag comfyui-manager yourusername/comfyui-manager:latest
docker push yourusername/comfyui-manager:latest
```

Or use the GitHub Actions workflow (automatic on push to main).

## Troubleshooting

### Container not found

- Verify `COMFYUI_CONTAINER_NAME` matches your ComfyUI container name exactly
- Run `docker ps` to see all running containers and their names
- Check the manager logs: `docker logs comfyui-manager`

### Cannot connect to ComfyUI

- Ensure `COMFYUI_HOST` matches your ComfyUI container name
- If containers are on different networks, use the container's IP address instead
- Verify port 8188 is correct for your setup
- Check that ComfyUI is actually running

### Docker socket permission denied

- The manager container needs access to the Docker socket
- Ensure `/var/run/docker.sock` is mounted correctly
- On some systems, you may need to adjust socket permissions

### Manager can't control ComfyUI container

- Both containers must have access to the same Docker daemon
- The Docker socket mount (`/var/run/docker.sock`) is required

## License

MIT License
