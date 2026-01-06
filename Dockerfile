FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY pyproject.toml requirements.txt ./
COPY src ./src

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

CMD ["python", "src/gradio_chat_agent/app.py"]
