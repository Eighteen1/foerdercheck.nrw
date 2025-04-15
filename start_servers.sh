#!/bin/bash

# Function to check if a port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Function to kill process on a port
kill_port() {
    local port=$1
    if check_port $port; then
        echo "Port $port is in use. Killing process..."
        lsof -ti:$port | xargs kill -9
        sleep 2
    fi
}

# Kill any existing processes on ports 8000 and 3000
kill_port 8000
kill_port 3000

# Start backend server
echo "Starting backend server..."
cd backend
python3 run.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend server
echo "Starting frontend server..."
cd ../frontend
npm start &
FRONTEND_PID=$!

# Function to handle script termination
cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up trap to catch termination signals
trap cleanup SIGINT SIGTERM

# Keep script running
echo "Both servers are running!"
echo "Press Ctrl+C to stop both servers"
wait 