"""
R1FS testing script.
This script is designed to run in a Docker container and perform the following tasks:
- Use the predefined location for checking the IPFS configuration file.
- start R1FS and run a loop every 15 seconds where it:
  - checks if the IPFS daemon is running
  - processes a command file where CIDs can be added
  - generates a random status file (YAML or Pickle) and adds it to IPFS
  - appends the CID of the generated file to a generated_cids.txt file
  

1: 12D3KooWNg4hRPtAv6QGE86zkmfDRk4maPLbMXraDKaESFiLuwwu
2: 12D3KooWE4ja3ie34b7mfiXs8XtrmxJCFxN7BCzPRePuRvWC1xy6

"""

import os
import time
import random
import pickle
import yaml
import json
import base64
import configparser
import subprocess
import signal
import sys
import uuid
from datetime import datetime

from ratio1.ipfs import R1FSEngine

__VER__ = "0.2.2"

  

# Global constants for file paths (to be mapped as volumes)
LOCAL_CACHE = '_local_cache'
COMMAND_FILE = os.path.join(LOCAL_CACHE, "commands.txt")
IPFS_CONFIG_FILE = os.path.join(LOCAL_CACHE, "ifps.ini")  # Contains EE_SWARM_KEY_CONTENT_BASE64 and EE_IPFS_RELAY

CYCLE_INTERVAL = 30

DEFAULT_CONFIG = """
[ipfs]
EE_SWARM_KEY_CONTENT_BASE64=
EE_IPFS_RELAY=
"""

class IPFSRunner:
  def __init__(self, logger):
    """
    Initialize the IPFSRunner:
      - Ensure required directories exist.
      - Initialize the IPFSWrapper.
      - Setup a flag to track if the IPFS daemon has been started.
    """
    self.shutdown_requested = False
    self.logger = logger
    
    self.spawn_subproc = False
    self.spawn_subproc_executed = False
    
    self.__last_generated_time = 0

    # Register signal handlers for graceful shutdown.
    signal.signal(signal.SIGINT, self.handle_shutdown)
    signal.signal(signal.SIGTERM, self.handle_shutdown)

    self.init_config()
    return
  
  def P(self, *args, **kwargs):
    self.logger.P(*args, **kwargs)
    return
  
  def init_config(self):
    """
    Initialize the config and command files if they don't exist.
    """

    if not os.path.isfile(IPFS_CONFIG_FILE):
      with open(IPFS_CONFIG_FILE, "w") as f:
        f.write(DEFAULT_CONFIG)
      self.P(f"IPFS config file '{IPFS_CONFIG_FILE}' created. Please provide required values.", color='y')
      
    if not os.path.isfile(COMMAND_FILE):
      with open(COMMAND_FILE, "w") as f:
        f.write("# Add CIDs here to process them.\n")
      self.P(f"Command file '{COMMAND_FILE}' created. Add CIDs to process.", color='y')
      
    self.spawn_subproc = os.environ.get("SUBPROC", "0").upper()  in ["1", "TRUE", "YES"]
    self.P(f"Initialized with spawn_subproc={self.spawn_subproc}", color='y')
    return

  def handle_shutdown(self, signum, frame):
    """
    Handle termination signals to gracefully shutdown the runner.
    """
    self.P("Shutdown signal received. Exiting...", color='y')
    self.shutdown_requested = True
    return

  def is_text_file(self, filename):
    """
    Returns True if the file extension indicates a text-based file.
    """
    lower = filename.lower()
    return lower.endswith(".txt") or lower.endswith(".json") or lower.endswith(".yaml") or lower.endswith(".yml")
  

  def is_pickle_file(self, filename):
    """
    Returns True if the file extension indicates a pickle file.
    """
    lower = filename.lower()
    return lower.endswith(".pkl") or lower.endswith(".pickle")


  def maybe_check_and_start_ipfs(self):
    """
    Check for the IPFS configuration file (ifps.ini). If found and IPFS is not yet fully started,
    perform the following:
      - Verify whether the IPFS repository is already initialized.
      - If not, write the swarm key to the IPFS repo and initialize the repo.
      - In any case, remove public bootstraps.
      - Start the IPFS daemon if it isnt running.
      - Connect to the specified relay and mark IPFS as started.
    Extra checks are added to handle container restarts where ~/.ipfs might already be initialized.
    """
    result = False
    
    if hasattr(self, "ipfs") and self.ipfs.ipfs_started:
      # IPFS is already started.
      return True

    if not os.path.isfile(IPFS_CONFIG_FILE):
      self.P(f"IPFS config file '{IPFS_CONFIG_FILE}' not found. Waiting for configuration...", color='y')
      return result

    config = configparser.ConfigParser()
    try:
      config.read(IPFS_CONFIG_FILE)
    except Exception as e:
      self.P(f"Error reading {IPFS_CONFIG_FILE}: {e}", color='r')
      return result

    if "ipfs" not in config:
      self.P(f"Section [ipfs] missing in {IPFS_CONFIG_FILE}.", color='r')
      return result

    swarm_key = config["ipfs"].get("EE_SWARM_KEY_CONTENT_BASE64")
    ipfs_relay = config["ipfs"].get("EE_IPFS_RELAY")

    if not swarm_key or not ipfs_relay:
      self.P("Missing required config values in ifps.ini. Please provide both EE_SWARM_KEY_CONTENT_BASE64 and EE_IPFS_RELAY.", color='r')
      return result
    
    os.environ['EE_IPFS_RELAY'] = ipfs_relay
    os.environ['EE_SWARM_KEY_CONTENT_BASE64'] = swarm_key
    
    self.ipfs = R1FSEngine(
      debug=True, 
      logger=self.logger
    )

    if self.ipfs.ipfs_started:
      self.P("IPFS daemon started successfully.", color='g')
      result = True
    return result


  def process_command_file(self):
    """
    Process the command file:
      - Read the file for CIDs (ignoring comments).
      - Clear the file after reading.
      - For each CID, pin it, download its content,
        and either display the file content (if text) or its size (if binary).
    """
    
    if not os.path.isfile(COMMAND_FILE):
      self.P(f"Command file '{COMMAND_FILE}' not found.", color='r')
      with open(COMMAND_FILE, "w") as f:
        f.write("# Add CIDs here to process them.\n")   
      return

    is_ipfs_warmed = self.ipfs.is_ipfs_warmed    

    try:
      with open(COMMAND_FILE, "r") as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    except Exception as e:
      self.P(f"Failed to read command file: {e}", color='r')
      return

    if not lines:
      # self.P("No CIDs found in command file.", color='d')
      return
    else:
      self.P(f"Found {len(lines)} CIDs in command file. Processing", color='g')

    failed_lines = []
    
    for line in lines:
      cid = line.split()[0]
      if len(line.split()) > 1:
        secret = line.split()[1]
      else:
        secret = None
      self.P(f"Processing CID: {cid} with secret: {secret}", color='g')
      try:
        is_avail = self.ipfs.is_cid_available(cid)
        if not is_avail:
          self.P(f"CID {cid} is not available in IPFS. {is_ipfs_warmed=}", color='r')
          failed_lines.append(line)
          continue
        self.P(f"Pinning CID {cid}...")
        file_path = self.ipfs.get_file(
          cid, local_folder=None, pin=True, timeout=10,
          secret=secret,
        )
        self.P(f"Downloaded file: {file_path}", color='g')
        if self.is_text_file(file_path):
          try:
            with open(file_path, "r", encoding="utf-8") as f:
              content = f.read()
            self.P(f"Content of {file_path}:\n{content}")
          except Exception as e:
            self.P(f"Error reading text file {file_path}: {e}", color='r')
        else:
          size = os.path.getsize(file_path)
          self.P(f"Binary file {file_path} size: {size} bytes", color='y')
          if self.is_pickle_file(file_path):
            with open(file_path, "rb") as f:
              content = pickle.load(f)
            self.P(f"Content of {file_path}:\n{json.dumps(content,indent=2)}")
      except Exception as e:
        self.P(f"Error processing CID {cid}: {e}", color='r')
    #end for cid
    
    if failed_lines:
      self.P(f"Failed to process the following CIDs: {', '.join(failed_lines)}", color='r')
    # Clear command file, leaving unsolved CIDs for next run.
    with open(COMMAND_FILE, "w") as f:
      f.write("# Add CIDs here to process them.\n")        
      for line in failed_lines:
        f.write(f"{line}\n")
    #end write 
    return
    

  def maybe_generate_status_file(self):
    """
    Generate a random status file (YAML or Pickle) containing:
      - Current timestamp.
      - IPFS peer ID.
      - List of pinned CIDs.
      - List of files in the downloads directory.
    The file is added to IPFS and its CID is appended to a generated_cids.txt file.
    """
    if time.time() - self.__last_generated_time < (CYCLE_INTERVAL * 10) and self.__last_generated_time > 0:
      return
    
    self.P("Generating local file to be deliverd for other nodes...")
      
    self.__last_generated_time = time.time()
    
    secured = random.choice([True, False])

    status = {
      "status" : {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id": self.ipfs.ipfs_id,
        "address": self.ipfs.ipfs_address,
        "agent" : self.ipfs.ipfs_agent,
        "downloaded_files": self.ipfs.downloaded_files,
        "uploaded_files": self.ipfs.uploaded_files,
        "secured": secured,
      }
    }
    
    if secured:
      secret = str(uuid.uuid4())[:4]
    else:
      secret = None

    file_type = "yaml" # random.choice(["yaml", "pickle"])
    str_now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"status_{str_now}.{ 'yaml' if file_type == 'yaml' else 'pkl' }"

    if file_type == "yaml":
      cid = self.ipfs.add_yaml(status, secret=secret)
    else:
      cid = self.ipfs.add_pickle(status, secret=secret)

    if cid is not None:
      try:
        self.P(f"Added {file_type} status file to IPFS with secret: {secret} CID: {cid}")
        with open("_local_cache/generated_cids.txt", "a") as f:
          f.write(f"{cid} {secret}\n")
      except Exception as e:
        self.P(f"Error adding status file to IPFS: {e}", color='r')
    return


  def run(self):
    """
    Run the main loop every 15 seconds:
      - Check and start IPFS if configuration is available.
      - Process the command file.
      - Generate a new status file.
    The loop runs until a shutdown is requested.
    """
    self.P(f"Starting IPFSRunner demo app v{__VER__}...", color='b', boxed=True)
    while not self.shutdown_requested:
      self.P("---- Cycle start ----", color='b')
      ipfs_started = self.maybe_check_and_start_ipfs()
      if ipfs_started:
        self.process_command_file()
        self.maybe_generate_status_file()
        if self.spawn_subproc and not self.spawn_subproc_executed:
          self.P("Starting subprocess...", color='b')
          self.spawn_subproc_executed = True
          try:            
            subprocess.Popen(["python3", "subproc.py"])
            self.P("Subprocess started. Sleeping...", color='g')            
            time.sleep(10)
          except Exception as e:
            self.P(f"Error starting subprocess: {e}", color='r')
      self.P(f"---- Cycle complete, sleeping {CYCLE_INTERVAL} seconds ----\n", color='b')
      time.sleep(CYCLE_INTERVAL)
    self.P("IPFSRunner shutting down.", color='y')
    return

if __name__ == "__main__":
  from ratio1 import Logger
  
  log = Logger("R1FSA", base_folder=".", app_folder=LOCAL_CACHE)
  runner = IPFSRunner(logger=log)
  runner.run()
