#!/bin/bash

set -e

# If we have swarm key content, save it to the IPFS repo
if [ -n "$SWARM_KEY_CONTENT_BASE64" ]; then
  echo "Writing swarm.key from env..."
  mkdir -p /root/.ipfs
  echo "$SWARM_KEY_CONTENT_BASE64" | base64 -d > /root/.ipfs/swarm.key
  echo "Using the following swarm.key:"
  cat /root/.ipfs/swarm.key
  chmod 600 /root/.ipfs/swarm.key
else
  echo "No SWARM_KEY_CONTENT_BASE64 environment variable set. Not writing swarm. Canceling run..."
  exit 1
fi

# Initialize IPFS if needed
if [ ! -d "/root/.ipfs" ] || [ ! -f "/root/.ipfs/config" ]; then
  ipfs init
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
echo "Starting FastAPI in $pwd"
uvicorn main:app --host 0.0.0.0 --port 8000
