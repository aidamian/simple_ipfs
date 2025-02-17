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
from datetime import datetime

from naeural_client.ipfs import R1FSEngine, log_info
  

# Global constants for file paths (to be mapped as volumes)
LOCAL_CACHE = './_local_cache'
COMMAND_FILE = os.path.join(LOCAL_CACHE, "commands.txt")
IPFS_CONFIG_FILE = os.path.join(LOCAL_CACHE, "ifps.ini")  # Contains EE_SWARM_KEY_CONTENT_BASE64 and EE_IPFS_RELAY

CYCLE_INTERVAL = 15

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
    
    self.__last_generated_time = 0

    # Register signal handlers for graceful shutdown.
    signal.signal(signal.SIGINT, self.handle_shutdown)
    signal.signal(signal.SIGTERM, self.handle_shutdown)

    self.init_config()
    return
  
  def P(self, *args, **kwargs):
    if hasattr(self, "logger"):
      self.logger.P(*args, **kwargs)
    else:
      log_info(*args, **kwargs)
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
    if hasattr(self, "ipfs") and self.ipfs.ipfs_started:
      return

    if not os.path.isfile(IPFS_CONFIG_FILE):
      self.P(f"IPFS config file '{IPFS_CONFIG_FILE}' not found. Waiting for configuration...", color='y')
      return

    config = configparser.ConfigParser()
    try:
      config.read(IPFS_CONFIG_FILE)
    except Exception as e:
      self.P(f"Error reading {IPFS_CONFIG_FILE}: {e}", color='r')
      return

    if "ipfs" not in config:
      self.P(f"Section [ipfs] missing in {IPFS_CONFIG_FILE}.", color='r')
      return

    swarm_key = config["ipfs"].get("EE_SWARM_KEY_CONTENT_BASE64")
    ipfs_relay = config["ipfs"].get("EE_IPFS_RELAY")

    if not swarm_key or not ipfs_relay:
      self.P("Missing required config values in ifps.ini. Please provide both EE_SWARM_KEY_CONTENT_BASE64 and EE_IPFS_RELAY.", color='r')
      return
    
    os.environ['EE_IPFS_RELAY'] = ipfs_relay
    os.environ['EE_SWARM_KEY_CONTENT_BASE64'] = swarm_key
    
    self.ipfs = R1FSEngine(debug=True, logger=self.logger)

    if self.ipfs.ipfs_started:
      self.P("IPFS daemon started successfully.", color='g')
    return


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
      return

    try:
      with open(COMMAND_FILE, "r") as f:
        cids = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
      # Clear command file, leaving header comment.
      with open(COMMAND_FILE, "w") as f:
        f.write("# Add CIDs here to process them.\n")
    except Exception as e:
      self.P(f"Failed to read command file: {e}", color='r')
      return

    if not cids:
      # self.P("No CIDs found in command file.", color='d')
      return

    for cid in cids:
      self.P(f"Processing CID: {cid}")
      try:
        file_path = self.ipfs.get_file(cid, local_folder=None, pin=True)
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
      except Exception as e:
        self.P(f"Error processing CID {cid}: {e}", color='r')

  def maybe_generate_status_file(self):
    """
    Generate a random status file (YAML or Pickle) containing:
      - Current timestamp.
      - IPFS peer ID.
      - List of pinned CIDs.
      - List of files in the downloads directory.
    The file is added to IPFS and its CID is appended to a generated_cids.txt file.
    """
    if time.time() - self.__last_generated_time < 60 and self.__last_generated_time > 0:
      return
      
    self.__last_generated_time = time.time()

    status = {
      "status" : {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id": self.ipfs.ipfs_id,
        "address": self.ipfs.ipfs_address,
        "agent" : self.ipfs.ipfs_agent,
        "downloaded_files": self.ipfs.downloaded_files,
        "uploaded_files": self.ipfs.uploaded_files,
      }
    }

    file_type = random.choice(["yaml", "pickle"])
    str_now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"status_{str_now}.{ 'yaml' if file_type == 'yaml' else 'pkl' }"

    if file_type == "yaml":
      cid = self.ipfs.add_yaml(status)
    else:
      cid = self.ipfs.add_pickle(status)

    try:
      self.P(f"Added {file_type} status file to IPFS. CID: {cid}")
      with open("generated_cids.txt", "a") as f:
        f.write(f"{cid}\n")
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
    self.P("Starting IPFSRunner demo app...", color='b')
    while not self.shutdown_requested:
      self.P("---- Cycle start ----", color='b')
      self.maybe_check_and_start_ipfs()
      if self.ipfs.ipfs_started:
        self.process_command_file()
        self.maybe_generate_status_file()
      self.P(f"---- Cycle complete, sleeping {CYCLE_INTERVAL} seconds ----\n", color='b')
      time.sleep(CYCLE_INTERVAL)
    self.P("IPFSRunner shutting down.", color='y')
    return

if __name__ == "__main__":
  log = Logger("R1FSA", base_folder=".", app_folder="_local_cache")
  runner = IPFSRunner(log=log)
  runner.run()
