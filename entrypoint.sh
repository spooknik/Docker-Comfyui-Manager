#!/bin/bash
# Entrypoint script for ComfyUI Manager
# This script starts the manager which then controls ComfyUI

set -e

# Default configuration
export COMFYUI_HOST=${COMFYUI_HOST:-"127.0.0.1"}
export COMFYUI_PORT=${COMFYUI_PORT:-"8189"}
export COMFYUI_START_CMD=${COMFYUI_START_CMD:-"python /root/ComfyUI/main.py --listen 127.0.0.1 --port 8189"}
export MANAGER_PORT=${MANAGER_PORT:-"8188"}
export IDLE_TIMEOUT_SECONDS=${IDLE_TIMEOUT_SECONDS:-"300"}
export IDLE_CHECK_INTERVAL=${IDLE_CHECK_INTERVAL:-"30"}

echo "========================================"
echo "ComfyUI Manager Starting"
echo "========================================"
echo "Manager port: $MANAGER_PORT"
echo "ComfyUI will listen on: $COMFYUI_HOST:$COMFYUI_PORT"
echo "Idle timeout: ${IDLE_TIMEOUT_SECONDS}s"
echo "========================================"

# Change to manager directory
cd /manager

# Start the manager with gunicorn
exec gunicorn \
    --bind "0.0.0.0:${MANAGER_PORT}" \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    app:app
