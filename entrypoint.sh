#!/bin/bash

set -e

# Initialize IPFS if not already initialized
if [ ! -d "/root/.ipfs" ]; then
  echo "Initializing IPFS..."
  ipfs init
fi

# Copy our swarm.key into the IPFS repo for a private network
if [ -f "/app/swarm.key" ]; then
  echo "Copying swarm key to ~/.ipfs/swarm.key"
  cp /app/swarm.key /root/.ipfs/swarm.key
  chmod 600 /root/.ipfs/swarm.key
fi

# (Optional) remove default public bootstraps so the node doesn't connect to the public network
echo "Removing public IPFS bootstraps (stay private)..."
ipfs bootstrap rm --all

# Start IPFS daemon in the background
echo "Starting IPFS daemon..."
ipfs daemon &

# Give the daemon a few seconds to fully come up
sleep 5

# If we have an environment variable for the relay, connect to it
# if the variable is not present then display error and cancel the run
if [ -n "$EE_IPFS_RELAY" ]; then
  echo "Attempting swarm connect to $EE_IPFS_RELAY"
  ipfs swarm connect "$EE_IPFS_RELAY" || true
else
  echo "ERROR: EE_IPFS_RELAY environment variable not set. Exiting..."
  exit 1
fi

# Start the FastAPI service
echo "Starting FastAPI..."
cd /app/src
uvicorn main:app --host 0.0.0.0 --port 8000
