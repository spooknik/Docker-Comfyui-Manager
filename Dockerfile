FROM python:3.11-slim

WORKDIR /manager

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY comfyui_manager.py .
COPY config.env.example config.env

# Expose the manager port
EXPOSE 80

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "1", "--threads", "4", "--timeout", "300", "app:app"]
