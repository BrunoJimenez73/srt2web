#!/bin/bash
# RTMP Server startup script
# This script starts the Node Media Server for RTMP input

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NMS_DIR="$SCRIPT_DIR/rtmp_server"

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed or not in PATH"
    exit 1
fi

# Check if node-media-server is installed
if [ ! -d "$NMS_DIR/node_modules" ]; then
    echo "Installing node-media-server..."
    cd "$NMS_DIR"
    npm install
fi

# Start the RTMP server
echo "Starting RTMP Server..."
cd "$NMS_DIR"
node server.js
