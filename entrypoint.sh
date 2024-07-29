#!/bin/bash

# Initialize IPFS
echo "Initializing IPFS..."
ipfs init

# Enable IPFS pubsub using the correct configuration
echo "Enabling IPFS pubsub..."
ipfs config Pubsub.Router gossipsub

# Start IPFS daemon with pubsub experiment enabled
echo "Starting IPFS daemon..."
ipfs daemon --enable-pubsub-experiment &
sleep 5

# Start the FastAPI app with uvicorn
echo "Starting FastAPI app..."
uvicorn main:app --host 0.0.0.0 --port 8000
