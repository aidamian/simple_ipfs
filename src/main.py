from fastapi import FastAPI, File, UploadFile, HTTPException, Request  # Import necessary modules from FastAPI
from fastapi.responses import HTMLResponse  # Import HTMLResponse to serve HTML content
from fastapi.staticfiles import StaticFiles  # Import StaticFiles to serve static files
from fastapi.templating import Jinja2Templates
import aiofiles  # Import aiofiles for asynchronous file handling
import os  # Import os for operating system interactions
import requests  # Import requests for making HTTP requests
import json  # Import json for handling JSON data
import asyncio  # Import asyncio for asynchronous operations
from datetime import datetime  # Import datetime for timestamping logs

__VER__ = "0.2.2"  # Define the version of the application



# Set up Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

INFO="""
## Simple IPFS Demo with FastAPI
- Upload files to IPFS using the HTTP API
- Publish file information to IPFS pub-sub
- Retrieve list of files from IPFS
"""

# Create a FastAPI application instance
app = FastAPI(
  title="Simple IPFS Demo",
  summary="Simple IPFS Demo with FastAPI",
  description=INFO,
  version=__VER__,
)  

# # Mount static files directory to serve the HTML client
# app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Directory to store temporarily uploaded files
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Ensure the upload directory exists

# IPFS API URL
IPFS_API_URL = "http://127.0.0.1:5001/api/v0"

# IPFS pubsub topic
TOPIC = "file_updates"

# ANSI color codes
COLOR_CODES = {
    "g": "\033[92m",  # Green
    "r": "\033[91m",  # Red
    "b": "\033[94m",  # Blue
    "y": "\033[93m",  # Yellow
    "reset": "\033[0m" # Reset color
}

def log_info(info: str, color: str = "reset"):
    """Log information with timestamp and color."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get the current timestamp
    color_code = COLOR_CODES.get(color, COLOR_CODES["reset"])  # Default to no color (reset) if the color is not found
    reset_code = COLOR_CODES["reset"]  # Reset to default color after the message
    print(f"{color_code}[{timestamp}] {info}{reset_code}", flush=True)
    

# Global in-memory store for files (in a real application, this could be a database)
file_store = {}

def process_pubsub_message(message: dict):
  """Process the received pubsub message and update the file list."""
  filename = message.get("filename")
  cid = message.get("cid")
  if filename and cid:
    log_info(f"Updating file store with {filename} - CID: {cid}")
    file_store[filename] = cid  # Update the in-memory store with the new file   
  return 

async def publish_to_ipfs_pubsub(filename: str, cid: str):
  """Publish file information to IPFS pub-sub."""
  pubsub_message = json.dumps({"filename": filename, "cid": cid})  # Create a JSON message with filename and CID
  log_info(f"Publishing to IPFS pubsub: {pubsub_message}")
  success = False  
  try:
    # Correctly set the topic and message using query parameters
    response = requests.post(
        f"{IPFS_API_URL}/pubsub/pub",
        params={"arg": [TOPIC, pubsub_message]}
    )
    response.raise_for_status()  # Raise an error if the request was not successful
    log_info("Successfully published to IPFS pubsub", color="g")
    success = True
  except requests.HTTPError as e:
    log_info(f"Failed to publish to IPFS pubsub: {e}", color="r")
  except Exception as e:
    log_info(f"Unexpected error: {e}", color="r")
  if not success:
    raise ValueError("publish_to_ipfs_pubsub: Failed to publish to IPFS pubsub")

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
  """Handle file upload and add to IPFS."""
  log_info(f"Received file upload request: {file.filename}")
  try:
    # Save uploaded file to temporary directory
    file_location = f"{UPLOAD_DIR}/{file.filename}"  # Determine the file path
    log_info(f"Saving file to: {file_location}")
    async with aiofiles.open(file_location, 'wb') as out_file:  # Open the file asynchronously for writing
      content = await file.read()  # Read the file content
      await out_file.write(content)  # Write the content to the file
    
    log_info(f"File saved: {file_location}")

    # Add file to IPFS using the HTTP API
    with open(file_location, 'rb') as file_data:  # Open the saved file for reading
      files = {'file': file_data}  # Prepare the file for upload
      log_info(f"Adding file to IPFS: {file_location}")
      response = requests.post(f"{IPFS_API_URL}/add", files=files)  # Add the file to IPFS
      response.raise_for_status()  # Raise an error if the request was not successful
      result = response.json()  # Parse the JSON response

    # Extract CID from the IPFS output
    cid = result["Hash"]  # Get the CID from the response
    log_info(f"File added to IPFS with CID: {cid}", color='g')  # Log the success message
    await publish_to_ipfs_pubsub(file.filename, cid)  # Publish the file info to the pubsub topic

    return {"filename": file.filename, "cid": cid}  # Return the filename and CID
  
  except Exception as e:  # Catch any exceptions
    log_info(f"Error during file upload: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))  # Raise an HTTP exception with the error message

@app.get("/ipfs-files/")
async def get_files():
  """Retrieve list of files from IPFS."""
  result = None
  log_info("Received request to list files from IPFS")
  try:
    url = f"{IPFS_API_URL}/files/ls"  # Prepare the URL to list files in IPFS
    log_info(f"Retrieving files from {url}")
    response = requests.post(url)  # List files in IPFS
    response.raise_for_status()  # Raise an error if the request was not successful
    json_data = response.json()
    files = json_data["Entries"]  # Get the file entries from the response
    log_info(f"Received from IPFS: {json_data}")
    result = {"files": files}  # Return the list of files  
  except Exception as e:  # Catch any exceptions
    log_info(f"Error retrieving files: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))  # Raise an HTTP exception with the error message  
  return result  # Return the list of files

@app.get("/files/")
async def get_files():
  """Retrieve list of files from the local store."""
  log_info("Received request to list files from the store")
  try:
    files = list(file_store.items())  # Convert dictionary to list of tuples
    log_info(f"Files available: {files}")
    return {"files": files}  # Return the list of files
  except Exception as e:
    log_info(f"Error retrieving files: {str(e)}", "r")
    raise HTTPException(status_code=500, detail="Failed to retrieve files")

@app.on_event("startup")
async def subscribe_to_pubsub():
  """Subscribe to IPFS pub-sub topic for file updates."""
  async def handle_pubsub_messages():
    log_info("Subscribing to IPFS pubsub topic")
    # Subscribe to the pubsub topic
    process = await asyncio.create_subprocess_exec("ipfs", "pubsub", "sub", TOPIC, stdout=asyncio.subprocess.PIPE)
    while True:
      line = await process.stdout.readline()  # Read a line from the pubsub subscription
      if line:
        message = json.loads(line.decode().strip())  # Decode and parse the message
        log_info(f"Received pubsub message: {message}", color='b')  # Log the received message
        process_pubsub_message(message)
      await asyncio.sleep(0.1)  # Sleep for a short period to avoid busy waiting
  
  asyncio.create_task(handle_pubsub_messages())  # Start the pubsub message handler as a background task
  log_info("Started pubsub message handler")
  return



@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
  """Serve the HTML file as a Jinja2 template with the IPFS peer ID."""
  try:
    # Fetch the peer ID from the IPFS node
    response = requests.post(f"{IPFS_API_URL}/id")
    response.raise_for_status()
    peer_info = response.json()
    peer_id = peer_info["ID"]
  except Exception as e:
    peer_id = "Unavailable"
  
  # Render the Jinja2 template with the peer_id
  return templates.TemplateResponse(
    "index.html", 
    {
      "request": request, 
      "peer_id": peer_id,
      "app_ver": __VER__,
    })