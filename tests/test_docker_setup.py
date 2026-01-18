import os

def test_dockerfile_exists():
    assert os.path.exists("Dockerfile")
    with open("Dockerfile", "r") as f:
        content = f.read()
        assert "FROM python:3.12-slim" in content
        assert "uv sync" in content
        assert "EXPOSE 7860" in content

def test_dockerignore_exists():
    assert os.path.exists(".dockerignore")
    with open(".dockerignore", "r") as f:
        content = f.read()
        assert ".git" in content
        assert ".venv" in content
