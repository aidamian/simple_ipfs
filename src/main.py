from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import aiofiles
import os
from datetime import datetime

# Import the new IPFS wrapper
from ipfs_utils.ipfs import IPFSWrapper

__VER__ = "0.2.4"

# 2-space indentation throughout
app = FastAPI(
  title="Simple IPFS Demo",
  summary="Simple IPFS Demo with FastAPI",
  version=__VER__,
)

templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "/app/uploads"
DOWNLOAD_DIR = "/app/downloads"

# ANSI color codes
COLOR_CODES = {
  "g": "\033[92m",  # Green
  "r": "\033[91m",  # Red
  "b": "\033[94m",  # Blue
  "y": "\033[93m",  # Yellow
  "reset": "\033[0m" # Reset color
}

def log_info(info: str, color: str = "reset"):
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  color_code = COLOR_CODES.get(color, COLOR_CODES["reset"])
  reset_code = COLOR_CODES["reset"]
  print(f"{color_code}[{timestamp}] {info}{reset_code}", flush=True)

# Create the IPFS wrapper instance
ipfs = IPFSWrapper(logger=log_info)

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
log_info("Directories created.")

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
  """Handle file upload and add to IPFS via the CLI wrapper."""
  log_info(f"Received file upload request: {file.filename}")
  try:
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    log_info(f"Saving file to: {file_location}")
    async with aiofiles.open(file_location, 'wb') as out_file:
      content = await file.read()
      await out_file.write(content)

    log_info(f"File saved: {file_location}", color='g')

    # Add file to IPFS
    cid = ipfs.add_file(file_location)
    log_info(f"File added to IPFS with CID: {cid}", color='g')
    return {"filename": file.filename, "cid": cid}

  except Exception as e:
    log_info(f"Error during file upload: {str(e)}", color='r')
    raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/")
async def get_files():
  """Retrieve the list of pinned CIDs from IPFS."""
  try:
    pinned_cids = ipfs.list_pins()
    return {"files": pinned_cids}
  except Exception as e:
    log_info(f"Error listing pinned files: {str(e)}", color='r')
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/file/{cid}")
async def get_file(cid: str):
  """Retrieve a file from IPFS and stream it."""
  local_filename = f"{DOWNLOAD_DIR}/downloaded_{cid}"
  try:
    ipfs.get_file(cid, local_filename)
    log_info(f"Downloaded file with CID {cid} -> {local_filename}")
    with open(local_filename, 'rb') as f:
      return Response(content=f.read(), media_type="application/octet-stream")
  except Exception as e:
    log_info(f"Error retrieving file {cid}: {str(e)}", color='r')
    raise HTTPException(status_code=500, detail=str(e))
  finally:
    if os.path.exists(local_filename):
      log_info(f"Removing downloaded file {local_filename}")
      os.remove(local_filename)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
  """Render the index page."""
  try:
    peer_id = ipfs.get_id()
  except Exception as e:
    log_info(f"Failed to get IPFS ID: {e}", color='r')
    peer_id = "Unavailable"

  return templates.TemplateResponse("index.html", {
    "request": request,
    "peer_id": peer_id,
    "app_ver": __VER__
  })
