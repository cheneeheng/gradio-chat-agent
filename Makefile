# -----------------------------
# Project Makefile
# -----------------------------

PYTHON := python3
PIP := pip

# -----------------------------
# Setup
# -----------------------------

install:
    $(PIP) install -r requirements.txt

dev:
    $(PIP) install -r requirements-dev.txt

# -----------------------------
# Linting & Formatting
# -----------------------------

lint:
    ruff check src tests

format:
    ruff format src tests

# -----------------------------
# Testing
# -----------------------------

test:
    pytest -q --disable-warnings --maxfail=1

test-all:
    pytest -vv

# -----------------------------
# Run Application
# -----------------------------

run:
    $(PYTHON) src/gradio_chat_agent/app.py

# -----------------------------
# Database
# -----------------------------

reset-db:
    rm -f gradio_chat_agent.db
    $(PYTHON) scripts/init_db.py

# -----------------------------
# Docker
# -----------------------------

docker-build:
    docker build -t gradio-chat-agent .

docker-run:
    docker-compose up

docker-stop:
    docker-compose down

# -----------------------------
# Utility
# -----------------------------

clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
