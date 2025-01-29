# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install IPFS
         
RUN wget https://dist.ipfs.tech/kubo/v0.32.1/kubo_v0.32.1_linux-amd64.tar.gz && \
  tar -xvzf kubo_v0.32.1_linux-amd64.tar.gz && \
  cd kubo && \
  bash install.sh

# Create a directory for the app
WORKDIR /app

# Copy the FastAPI app
ADD requirements.txt /app
ADD entrypoint.sh /app
COPY ./src /app

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Copy and set up the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the FastAPI port
EXPOSE 8000 

# Run the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
