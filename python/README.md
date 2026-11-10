# Simple Flask Application

This is a simple Flask application that demonstrates basic API endpoints and a user interface for inputting and displaying numbers.

## Features

- **API Endpoints**: The application provides several API endpoints that return JSON responses.
- **Logging**: All requests are logged with details including the timestamp, method, URL, and User-Agent.
- **User Interface**: A simple web interface where users can input a number, which is then displayed back to them.

## Prerequisites

Before you run this application, you'll need [uv](https://docs.astral.sh/uv/getting-started/installation/) installed. The dependencies (Flask, requests) are defined in the `pyproject.toml` in the repository root. Install them once from the repository root:

```bash
uv sync
```

Start the app from this directory

```bash
uv run python main.py
```

## Access the user interface

Open the browser and navigate to the address below

```bash
http://localhost:8000/ui
```
