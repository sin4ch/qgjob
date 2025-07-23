#!/bin/bash

echo "Starting QualGent Job Orchestrator..."

if [ "$1" = "api" ]; then
    echo "Starting API server..."
    python -m qgjob.main
elif [ "$1" = "worker" ]; then
    echo "Starting worker process..."
    python -m qgjob.worker
elif [ "$1" = "dev" ]; then
    echo "Starting development environment..."
    docker-compose up
else
    echo "Usage: ./scripts/start.sh [api|worker|dev]"
    echo "  api    - Start API server only"
    echo "  worker - Start worker process only"
    echo "  dev    - Start full development environment with Docker"
fiStarting QualGent Job Orchestrator..."

if [ "$1" = "api" ]; then
    echo "Starting API server..."
    python main.py
elif [ "$1" = "worker" ]; then
    echo "Starting worker process..."
    python worker.py
elif [ "$1" = "dev" ]; then
    echo "Starting development environment..."
    docker-compose up
else
    echo "Usage: ./start.sh [api|worker|dev]"
    echo "  api    - Start API server only"
    echo "  worker - Start worker process only"
    echo "  dev    - Start full development environment with Docker"
fi
