"""
Reverse proxy for ComfyUI with wake-on-access support.
Automatically starts the container when a request arrives.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

import httpx
from fastapi import Request, Response
from fastapi.responses import HTMLResponse

from .config import get_config
from .docker_manager import docker_manager, ContainerState
from .comfyui_client import comfyui_client

logger = logging.getLogger(__name__)


def get_starting_page(message: str = "The container was stopped to save resources. Please wait while it starts up.") -> str:
    """Generate the starting page HTML with a custom message."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>ComfyUI - Starting...</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
        }}
        .container {{
            text-align: center;
            padding: 40px;
        }}
        .spinner {{
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255,255,255,0.1);
            border-top-color: #4ade80;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        p {{
            color: #aaa;
            font-size: 14px;
        }}
        .status {{
            margin-top: 20px;
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            font-size: 12px;
        }}
        .manager-link {{
            margin-top: 30px;
        }}
        .manager-link a {{
            color: #4ade80;
            text-decoration: none;
        }}
        .manager-link a:hover {{
            text-decoration: underline;
        }}
    </style>
    <script>
        // Check if ComfyUI is ready every 3 seconds
        async function checkReady() {{
            try {{
                const response = await fetch('/api/status');
                const data = await response.json();
                if (data.queue && data.queue.connected) {{
                    // ComfyUI is ready, reload to proxy through
                    window.location.reload();
                }}
            }} catch (e) {{
                console.log('Still waiting...', e);
            }}
        }}
        setInterval(checkReady, 3000);
        setTimeout(checkReady, 1000);
    </script>
</head>
<body>
    <div class="container">
        <div class="spinner"></div>
        <h1>ComfyUI is starting...</h1>
        <p>{message}</p>
        <div class="status">Checking status automatically...</div>
        <div class="manager-link">
            <a href="/manager">Open Manager Dashboard</a>
        </div>
    </div>
</body>
</html>
"""


class ProxyHandler:
    """Handles reverse proxy requests to ComfyUI."""

    def __init__(self):
        self._starting: bool = False
        self._start_time: Optional[datetime] = None

    async def handle_request(self, request: Request) -> Response:
        """Handle an incoming request, starting container if needed."""
        config = get_config()

        # Update activity timestamp for any incoming request
        comfyui_client.update_activity()

        # Check container status
        status = docker_manager.get_status()
        container_state = status.get("state")

        logger.debug(f"Proxy request: path={request.url.path}, state={container_state}, starting={self._starting}")

        # If container is running, try to proxy the request
        if container_state == ContainerState.RUNNING.value:
            response = await self._proxy_request(request)
            if response is not None:
                return response
            # Proxy failed, ComfyUI not ready yet
            return HTMLResponse(
                content=get_starting_page("Container is running, waiting for ComfyUI to initialize..."),
                status_code=503
            )

        # If container is starting, show waiting page
        if container_state == ContainerState.STARTING.value or self._starting:
            return HTMLResponse(
                content=get_starting_page("Container is starting up..."),
                status_code=503
            )

        # Container is stopped - start it if auto-start is enabled
        if config.auto_start_enabled:
            return await self._start_and_wait(request)
        else:
            return HTMLResponse(
                content="""
                <html>
                <head><title>ComfyUI Stopped</title></head>
                <body style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #1a1a2e; color: #eee;">
                    <div style="text-align: center;">
                        <h1>ComfyUI is stopped</h1>
                        <p>Auto-start is disabled.</p>
                        <p><a href="/manager" style="color: #4ade80;">Open Manager Dashboard</a> to start it manually.</p>
                    </div>
                </body>
                </html>
                """,
                status_code=503
            )

    async def _start_and_wait(self, request: Request) -> Response:
        """Start the container and return a waiting page."""
        if not self._starting:
            self._starting = True
            self._start_time = datetime.now()

            logger.info("Auto-starting ComfyUI container due to incoming request")

            result = await docker_manager.start_container()

            if not result.get("success"):
                self._starting = False
                return HTMLResponse(
                    content=f"""
                    <html>
                    <head><title>Start Failed</title></head>
                    <body style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #1a1a2e; color: #eee;">
                        <div style="text-align: center;">
                            <h1>Failed to start ComfyUI</h1>
                            <p style="color: #f87171;">{result.get('error')}</p>
                            <p><a href="/manager" style="color: #4ade80;">Open Manager Dashboard</a></p>
                        </div>
                    </body>
                    </html>
                    """,
                    status_code=500
                )

            asyncio.create_task(self._wait_for_ready())

        return HTMLResponse(
            content=get_starting_page("Starting the container..."),
            status_code=503
        )

    async def _wait_for_ready(self) -> None:
        """Wait for ComfyUI to become ready."""
        config = get_config()

        try:
            ready = await comfyui_client.wait_for_ready(config.startup_timeout_seconds)
            if ready:
                logger.info("ComfyUI is now ready to accept requests")
            else:
                logger.warning("ComfyUI did not become ready in time")
        finally:
            self._starting = False

    async def _proxy_request(self, request: Request) -> Optional[Response]:
        """Proxy the request to ComfyUI. Returns None if connection fails."""
        config = get_config()

        # Use the request path directly - no prefix stripping needed
        path = request.url.path
        if not path:
            path = "/"

        target_url = f"{config.comfyui_url}{path}"
        if request.url.query:
            target_url += f"?{request.url.query}"

        logger.debug(f"Proxying to: {target_url}")

        body = await request.body()

        headers = {}
        hop_by_hop = {"connection", "keep-alive", "transfer-encoding", "te", "trailers", "upgrade"}
        for key, value in request.headers.items():
            if key.lower() not in hop_by_hop and key.lower() != "host":
                headers[key] = value

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    follow_redirects=False
                )

                content = response.content

                response_headers = {}
                for key, value in response.headers.items():
                    if key.lower() not in hop_by_hop:
                        response_headers[key] = value

                return Response(
                    content=content,
                    status_code=response.status_code,
                    headers=response_headers
                )

        except httpx.ConnectError:
            logger.debug("Cannot connect to ComfyUI - not ready yet")
            return None
        except httpx.TimeoutException:
            logger.warning("Timeout connecting to ComfyUI")
            return None
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            return HTMLResponse(
                content=f"<h1>Proxy Error</h1><p>{str(e)}</p>",
                status_code=502
            )


# Global proxy handler instance
proxy_handler = ProxyHandler()
