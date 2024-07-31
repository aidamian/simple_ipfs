from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Response  # Import necessary modules from FastAPI
from fastapi.responses import HTMLResponse  # Import HTMLResponse to serve HTML content
from fastapi.staticfiles import StaticFiles  # Import StaticFiles to serve static files
from fastapi.templating import Jinja2Templates
import aiofiles  # Import aiofiles for asynchronous file handling
import os  # Import os for operating system interactions
import requests  # Import requests for making HTTP requests
import json  # Import json for handling JSON data
import asyncio  # Import asyncio for asynchronous operations
from datetime import datetime  # Import datetime for timestamping logs

from ipfs_utils.ipfs import ipfs_add_file, ipfs_list_pin_files, ipfs_get_id

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
    return
    

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
  """Handle file upload and add to IPFS."""
  result = None
  log_info(f"Received file upload request: {file.filename}")
  try:
    # Save uploaded file to temporary directory
    file_location = f"{UPLOAD_DIR}/{file.filename}"  # Determine the file path
    log_info(f"Saving file to: {file_location}")
    async with aiofiles.open(file_location, 'wb') as out_file:  # Open the file asynchronously for writing
      content = await file.read()  # Read the file content
      await out_file.write(content)  # Write the content to the file
    
    log_info(f"File saved: {file_location}")
    cid = ipfs_add_file(file_location, IPFS_API_URL, log_info=log_info)  # Add the file to IPFS
    log_info(f"File added to IPFS with CID: {cid}", color='g')  # Log the success message

    result = {"filename": file.filename, "cid": cid}  # Return the filename and CID 
  except Exception as e:  # Catch any exceptions
    log_info(f"Error during file upload: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))  # Raise an HTTP exception with the error message
  return result


@app.get("/files/")
async def get_files_ls():
  """Retrieve list of files from IPFS."""
  result = None
  log_info("Received request to list files from IPFS")
  try:
    files = ipfs_list_pin_files(IPFS_API_URL, log_info=log_info)  # List files in IPFS
    result = {"files": files}  # Return the list of files  
  except Exception as e:  # Catch any exceptions
    log_info(f"Error retrieving files: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))  # Raise an HTTP exception with the error message  
  return result  # Return the list of files


@app.get("/file/{cid}")
async def get_file(cid: str):
  """Retrieve a file from IPFS given its CID."""
  try:
    log_info(f"Fetching file with CID: {cid}")
    response = requests.post(f"{IPFS_API_URL}/get?arg={cid}")
    response.raise_for_status()
    return Response(content=response.content, media_type="application/octet-stream")
  except Exception as e:
    log_info(f"Error fetching file with CID {cid}: {str(e)}", color='r')
    raise HTTPException(status_code=500, detail=f"Unable to fetch file: {e}")



@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
  """Serve the HTML file as a Jinja2 template with the IPFS peer ID."""
  peer_id = ipfs_get_id(IPFS_API_URL)  # Get the IPFS peer ID  
  # Render the Jinja2 template with the peer_id
  return templates.TemplateResponse(
    "index.html", 
    {
      "request": request, 
      "peer_id": peer_id,
      "app_ver": __VER__,
  })