# ComfyUI Manager

A lightweight proxy application that sits in front of ComfyUI and automatically starts/stops it based on user activity. This saves GPU power when ComfyUI is not being used.

## Features

- **Auto-start**: ComfyUI starts automatically when you access the web interface
- **Auto-stop**: ComfyUI stops after a configurable idle timeout (default: 5 minutes)
- **Web UI**: Simple management interface to manually start/stop and monitor status
- **Transparent proxy**: All ComfyUI requests are proxied seamlessly
- **Activity tracking**: Any request to ComfyUI resets the idle timer

## Quick Start with Docker Hub (Easiest for TrueNAS)

Pull the pre-built image from Docker Hub:

```bash
docker pull <your-dockerhub-username>/comfyui-manager:latest

docker run -d \
  --gpus all \
  -p 8188:8188 \
  -v /path/to/models:/root/ComfyUI/models \
  -v /path/to/output:/root/ComfyUI/output \
  -v /path/to/custom_nodes:/root/ComfyUI/custom_nodes \
  -e IDLE_TIMEOUT_SECONDS=300 \
  --name comfyui-managed \
  <your-dockerhub-username>/comfyui-manager:latest
```

**For TrueNAS Scale:**
1. Go to Apps > Discover Apps > Custom App
2. Configure:
   - **Image Repository**: `<your-dockerhub-username>/comfyui-manager`
   - **Image Tag**: `latest`
   - **Port**: Map `8188` to your desired external port
   - **GPU**: Enable GPU passthrough in Resources
   - **Storage**: Mount your existing ComfyUI volumes:
     - `/mnt/your-pool/comfyui/models` → `/root/ComfyUI/models`
     - `/mnt/your-pool/comfyui/output` → `/root/ComfyUI/output`
     - `/mnt/your-pool/comfyui/custom_nodes` → `/root/ComfyUI/custom_nodes`
   - **Environment Variables**:
     - `IDLE_TIMEOUT_SECONDS=300` (or your preferred timeout)

3. Deploy and access at `http://your-truenas-ip:8188/manager`

## Installation with YanWenKun/ComfyUI-Docker

### Option 1: Custom Dockerfile (Recommended for Self-Build)

Create a custom Dockerfile that extends the ComfyUI-Docker image:

```dockerfile
# Dockerfile.managed
FROM yanwenkun/comfyui-boot:latest

# Install manager dependencies
RUN pip install flask requests gunicorn python-dotenv

# Copy manager files
COPY app.py /manager/
COPY comfyui_manager.py /manager/
COPY entrypoint.sh /manager/

RUN chmod +x /manager/entrypoint.sh

# Expose manager port instead of ComfyUI port
EXPOSE 80

# Use manager as entrypoint
ENTRYPOINT ["/manager/entrypoint.sh"]
```

Then build and run:
```bash
docker build -f Dockerfile.managed -t comfyui-managed .
docker run -d \
  --gpus all \
  -p 8188:80 \
  -v /path/to/models:/root/ComfyUI/models \
  -v /path/to/output:/root/ComfyUI/output \
  -e IDLE_TIMEOUT_SECONDS=300 \
  comfyui-managed
```

### Option 2: Mount into existing container

If you prefer to mount the manager into an existing container:

1. Copy the manager files to a directory on your host
2. Mount that directory and override the entrypoint:

```yaml
# docker-compose.yml
version: "3.8"
services:
  comfyui:
    image: yanwenkun/comfyui-boot:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "8188:8188"  # Map to manager port
    volumes:
      - ./manager:/manager:ro
      - /path/to/models:/root/ComfyUI/models
      - /path/to/output:/root/ComfyUI/output
    environment:
      - IDLE_TIMEOUT_SECONDS=300
      - COMFYUI_START_CMD=python /root/ComfyUI/main.py --listen 127.0.0.1 --port 8189
    entrypoint: ["/bin/bash", "-c", "pip install flask requests gunicorn python-dotenv && /manager/entrypoint.sh"]
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMFYUI_HOST` | `127.0.0.1` | Host where ComfyUI runs (internal) |
| `COMFYUI_PORT` | `8189` | Internal port ComfyUI listens on |
| `COMFYUI_START_CMD` | `python /root/ComfyUI/main.py --listen 127.0.0.1 --port 8189` | Command to start ComfyUI |
| `MANAGER_PORT` | `8188` | Port the manager listens on (external) |
| `IDLE_TIMEOUT_SECONDS` | `300` | Seconds of inactivity before stopping ComfyUI |
| `IDLE_CHECK_INTERVAL` | `30` | How often to check for idle (seconds) |

## Usage

1. Access the manager UI at `http://your-server:8188/manager`
2. Click "Start" to manually start ComfyUI, or just go to `http://your-server:8188/` - it will auto-start
3. Use ComfyUI normally - the manager proxies all requests
4. After the idle timeout with no activity, ComfyUI automatically stops
5. Next time you access it, it auto-starts again

## How It Works

```
                                    ┌─────────────────────┐
                                    │   ComfyUI Manager   │
    User Request ──────────────────►│   (Flask + Proxy)   │
         :8188                      │      port 8188      │
                                    │  - Auto-start       │
                                    │  - Activity track   │
                                    │  - Idle shutdown    │
                                    └──────────┬──────────┘
                                               │
                                               ▼
                                    ┌─────────────────────┐
                                    │      ComfyUI        │
                                    │   (127.0.0.1:8189)  │
                                    │                     │
                                    │  Starts on demand   │
                                    │  Stops when idle    │
                                    └─────────────────────┘
```

## TrueNAS Setup

For TrueNAS Scale with Apps:

1. Create an app from a custom Docker image or use Docker Compose
2. Make sure to:
   - Map the external port to port 80 (the manager), not 8188
   - Mount your models and output directories
   - Set the `COMFYUI_START_CMD` if needed for your setup

Example TrueNAS docker-compose:
```yaml
version: "3.8"
services:
  comfyui-managed:
    build:
      context: .
      dockerfile: Dockerfile.managed
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - IDLE_TIMEOUT_SECONDS=300
    ports:
      - "8188:8188"
    volumes:
      - /mnt/pool/appdata/comfyui/models:/root/ComfyUI/models
      - /mnt/pool/appdata/comfyui/output:/root/ComfyUI/output
      - /mnt/pool/appdata/comfyui/custom_nodes:/root/ComfyUI/custom_nodes
    restart: unless-stopped
```

## Power Savings

With a 5-minute idle timeout:
- ComfyUI runs: ~15W GPU power
- ComfyUI stopped: ~0W GPU power (GPU idles)
- If you use ComfyUI for 2 hours/day, you save power the other 22 hours
