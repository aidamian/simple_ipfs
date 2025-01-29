from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import aiofiles
import os
import shutil
from datetime import datetime

from ipfs_utils.ipfs import IPFSWrapper  # import from your local ipfs.py

__VER__ = "0.3.0"

app = FastAPI(
  title="Wrapped IPFS Demo",
  version=__VER__,
)

templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "/app/uploads"
DOWNLOAD_DIR = "/app/downloads"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COLOR_CODES = {
  "g": "\033[92m",
  "r": "\033[91m",
  "b": "\033[94m",
  "y": "\033[93m",
  "reset": "\033[0m"
}

def log_info(msg: str, color="reset"):
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  color_code = COLOR_CODES.get(color, COLOR_CODES["reset"])
  reset_code = COLOR_CODES["reset"]
  print(f"{color_code}[{timestamp}] {msg}{reset_code}", flush=True)

ipfs = IPFSWrapper(logger=log_info)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
  """
  Handle file upload, add to IPFS with '-w' so a folder is created containing the original file name.
  Returns the folder CID.
  """
  try:
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    async with aiofiles.open(file_location, 'wb') as out_file:
      content = await file.read()
      await out_file.write(content)

    folder_cid = ipfs.add_file(file_location)
    log_info(f"Uploaded file {file.filename}, got folder CID: {folder_cid}", color="g")

    return {"filename": file.filename, "cid": folder_cid}
  except Exception as e:
    log_info(f"Error uploading file: {str(e)}", color="r")
    raise HTTPException(status_code=500, detail=str(e))

@app.post("/pin/{cid}")
def pin_cid(cid: str):
  """
  Manually pin a user-provided CID so it appears in local pinset.
  This is helpful if the user wants to fetch data from another node by known CID.
  """
  try:
    output = ipfs.pin_add(cid)
    log_info(f"Manually pinned CID: {cid}", color="b")
    return {"cid": cid, "output": output}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/")
def list_files():
  """List pinned folder CIDs."""
  try:
    pinned = ipfs.list_pins()
    return {"files": pinned}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@app.get("/file/{cid}")
def download_file(cid: str):
  """
  Given a folder CID (from 'ipfs add -w'), we 'ipfs get' it,
  then find the single file within that folder and return it with the original filename.
  """
  folder_path = os.path.join(DOWNLOAD_DIR, cid)
  try:
    # 1. ipfs get the folder
    ipfs.get_file(cid, folder_path)
    # Now folder_path contains 1 or more files (the original name(s)).

    # 2. Assuming there's exactly one file (the typical case for '-w' with a single file).
    entries = os.listdir(folder_path)
    if len(entries) != 1:
      # If more than one file, or zero, handle accordingly
      raise Exception(f"Expected exactly 1 file in folder, found {entries}")

    original_name = entries[0]
    file_full_path = os.path.join(folder_path, original_name)

    with open(file_full_path, 'rb') as f:
      data = f.read()

    # Return it with the original file name in Content-Disposition
    return Response(
      content=data,
      media_type="application/octet-stream",
      headers={
        "Content-Disposition": f'attachment; filename="{original_name}"'
      }
    )
  except Exception as e:
    log_info(f"Error retrieving file for CID {cid}: {str(e)}", color="r")
    raise HTTPException(status_code=500, detail=str(e))
  finally:
    # Clean up local folder
    if os.path.exists(folder_path):
      shutil.rmtree(folder_path)
      log_info(f"Removed temp folder {folder_path}", color="y")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
  """Serve the index page with the form for upload + manual pin + list pinned files."""
  try:
    peer_id = ipfs.get_id()
  except Exception as e:
    log_info(f"Failed to get IPFS ID: {e}", color="r")
    peer_id = "Unavailable"

  return templates.TemplateResponse("index.html", {
    "request": request,
    "peer_id": peer_id,
    "app_ver": __VER__
  })
