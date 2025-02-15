"""
Ratio1 base IPFS utility functions.

"""
import subprocess
import json
from datetime import datetime
import base64
import time
import os
import tempfile



class IPFSCt:
  EE_IPFS_RELAY_ENV_KEY = "EE_IPFS_RELAY"
  EE_SWARM_KEY_CONTENT_BASE64_ENV_KEY = "EE_SWARM_KEY_CONTENT_BASE64"
  TEMP = "./_local_cache/_output/ipfs_downloads"

ERROR_TAG = "Unknown"

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
  return

class SimpleLogger:
  def P(self, *args, **kwargs):
    log_info(*args, **kwargs)
    return


class IPFSWrapper:
  def __init__(self, logger=None, downloads_dir=None):
    """
    Initialize the IPFS wrapper with a given logger function.
    By default, it uses the built-in print function for logging.
    """
    self.logger = logger
    if logger is None:
      logger = SimpleLogger()

    self.__ipfs_started = False
    self.__ipfs_address = None
    self.__ipfs_id = None
    self.__ipfs_agent = None
    self.__uploaded_files = {}
    self.__downloaded_files = {}

    if downloads_dir is None:
      if hasattr(logger, "get_output_folder"):
        downloads_dir = logger.get_output_folder()
      else:
        downloads_dir = IPFSCt.TEMP
    self.__downloads_dir = downloads_dir
    os.makedirs(self.__downloads_dir, exist_ok=True)
    return
    
  def P(self, *args, **kwargs):
    self.logger.P(*args, **kwargs)
    return
    
  @property
  def ipfs_id(self):
    return self.__ipfs_id
  
  @property
  def ipfs_address(self):
    return self.__ipfs_address
  
  @property
  def ipfs_agent(self):
    return self.__ipfs_agent
  
  @property
  def ipfs_started(self):
    return self.__ipfs_started
  
  @property
  def uploaded_files(self):
    return self.__uploaded_files
  
  @property
  def downloaded_files(self):
    return self.__downloaded_files


  def run_command(self, cmd_list, verbose=False, raise_on_error=True):
    """
    Run a shell command using subprocess and return the stdout.
    Also log the command and its result.
    """
    cmd_str = " ".join(cmd_list)
    if verbose:
      self.P(f"Running command: {cmd_str}")
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if result.returncode != 0:
      self.P(f"Command error: {result.stderr.strip()}")
      if raise_on_error:
        raise Exception(f"Error while running '{cmd_str}': {result.stderr.strip()}")
    if verbose:
      self.P(f"Command output: {result.stdout.strip()}")
    return result.stdout.strip()
  
  
  def add_json(self, data) -> bool:
    """
    Add a JSON object to IPFS.
    """
    try:
      json_data = json.dumps(data)
      with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(json_data)
      cid = self.add_file(f.name)
      return cid
    except Exception as e:
      self.P(f"Error adding JSON to IPFS: {e}", color='r')
      return None
    
    
  def add_yaml(self, data, fn=None) -> bool:
    """
    Add a YAML object to IPFS.
    """
    try:
      import yaml
      yaml_data = yaml.dump(data)
      with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_data)
      cid = self.add_file(f.name)
      return cid
    except Exception as e:
      self.P(f"Error adding YAML to IPFS: {e}", color='r')
      return None
    
    
  def add_pickle(self, data) -> bool:
    """
    Add a Pickle object to IPFS.
    """
    try:
      with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
        import pickle
        pickle.dump(data, f)
      cid = self.add_file(f.name)
      return cid
    except Exception as e:
      self.P(f"Error adding Pickle to IPFS: {e}", color='r')
      return None


  def add_file(self, file_path: str) -> str:
    """
    Add a file to IPFS via 'ipfs add -q'.
    Returns the CID of the added file.
    
    TODO: add another add/pin to get the CID of the metadata file so each file will 
    have a CID for the file and a CID for the metadata.
    """
    output = self.run_command(["ipfs", "add", "-q", "-w", file_path])
    # "ipfs add -w <file>" typically prints two lines:
    #   added <hash_of_file> <filename>
    #   added <hash_of_wrapped_folder> <foldername?>
    # We want the *last* line's CID (the wrapped folder).
    lines = output.strip().split("\n")
    if not lines:
      raise Exception("No output from 'ipfs add -w -q'")
    folder_cid = lines[-1].strip()
    self.__uploaded_files[folder_cid] = file_path
    return folder_cid


  def get_file(self, cid: str, local_folder: str = None, pin=True) -> str:
    """
    Get a file from IPFS by CID and save it to a local folder.
    If no local folder is provided, the default downloads directory is used.
    Returns the full path of the downloaded file.
    
    Parameters
    ----------
    cid : str
        The CID of the file to download.
    local_folder : str
        The local folder to save the
            
    """
    if pin:
      pin_result = self.pin_add(cid)
      
    if local_folder is None:
      local_folder = self.__downloads_dir # default downloads directory
      os.makedirs(local_folder, exist_ok=True)
      local_folder = os.path.join(local_folder, cid) # add the CID as a subfolder
      
    
    self.run_command(["ipfs", "get", cid, "-o", local_folder])
    # now we need to get the file from the folder
    folder_contents = os.listdir(local_folder)
    if len(folder_contents) != 1:
      raise Exception(f"Expected one file in {local_folder}, found {folder_contents}")
    # get the full path of the file
    out_local_filename = os.path.join(local_folder, folder_contents[0])
    self.__downloaded_files[cid] = out_local_filename
    return out_local_filename


  def pin_add(self, cid: str) -> str:
    """
    Explicitly pin a CID (and fetch its data) so it appears in the local pinset.
    """
    res = self.run_command(["ipfs", "pin", "add", cid])  
    return res
    


  def list_pins(self):
    """
    List pinned CIDs via 'ipfs pin ls --type=recursive'.
    Returns a list of pinned CIDs.
    """
    output = self.run_command(["ipfs", "pin", "ls", "--type=recursive"])
    pinned_cids = []
    for line in output.split("\n"):
      line = line.strip()
      if not line:
        continue
      parts = line.split()
      if len(parts) > 0:
        pinned_cids.append(parts[0])
    return pinned_cids


  def get_id(self) -> str:
    """
    Get the IPFS peer ID via 'ipfs id' (JSON output).
    Returns the 'ID' field as a string.
    """
    output = self.run_command(["ipfs", "id"])
    try:
      data = json.loads(output)
      self.__ipfs_id = data.get("ID", ERROR_TAG)
      self.__ipfs_address = data.get("Addresses", [ERROR_TAG,ERROR_TAG])[1]
      self.__ipfs_agent = data.get("AgentVersion", ERROR_TAG)
      return data.get("ID", ERROR_TAG)
    except json.JSONDecodeError:
      raise Exception("Failed to parse JSON from 'ipfs id' output.")



  def maybe_start_ipfs(self, base64_swarm_key: str = None, ipfs_relay: str = None) -> bool:
    """
    This method initializes the IPFS repository if needed, connects to a relay, and starts the daemon.
    """
    if self.ipfs_started:
      return
    
    if base64_swarm_key is None:
      base64_swarm_key = os.getenv(IPFSCt.EE_SWARM_KEY_CONTENT_BASE64_ENV_KEY)
      
    if ipfs_relay is None:
      ipfs_relay = os.getenv(IPFSCt.EE_IPFS_RELAY_ENV_KEY)
    
    if not base64_swarm_key or not ipfs_relay:
      self.P("Missing required config values. Please provide both EE_SWARM_KEY_CONTENT_BASE64 and EE_IPFS_RELAY.", color='r')
      return False
    
    ipfs_repo = os.path.expanduser("~/.ipfs")
    os.makedirs(ipfs_repo, exist_ok=True)
    config_path = os.path.join(ipfs_repo, "config")
    swarm_key_path = os.path.join(ipfs_repo, "swarm.key")

    if not os.path.isfile(config_path):
      # Repository is not initialized; write the swarm key and init.
      try:
        decoded_key = base64.b64decode(base64_swarm_key)
        with open(swarm_key_path, "wb") as f:
          f.write(decoded_key)
        os.chmod(swarm_key_path, 0o600)
        self.P("Swarm key written successfully.", color='g')
      except Exception as e:
        self.P(f"Error writing swarm.key: {e}", color='r')
        return False

      try:
        self.P("Initializing IPFS repository...")
        self.run_command(["ipfs", "init"])
      except Exception as e:
        self.P(f"Error during IPFS init: {e}", color='r')
        return False
    else:
      self.P(f"IPFS repository already initialized in {config_path}.", color='g')

    try:
      self.P("Removing public IPFS bootstrap nodes...")
      self.run_command(["ipfs", "bootstrap", "rm", "--all"])
    except Exception as e:
      self.P(f"Error removing bootstrap nodes: {e}", color='r')

    # Check if daemon is already running by attempting to get the node id.
    try:
      # explicit run no get_id
      result = self.run_command(["ipfs", "id"])
      self.__ipfs_id = json.loads(result)["ID"]
      self.__ipfs_address = json.loads(result)["Addresses"][1]
      self.__ipfs_agent = json.loads(result)["AgentVersion"]
      self.P("IPFS daemon running", color='g')
            
    except Exception:
      try:
        self.P("Starting IPFS daemon in background...")
        subprocess.Popen(["ipfs", "daemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
      except Exception as e:
        self.P(f"Error starting IPFS daemon: {e}", color='r')
        return

    try:
      my_id = self.get_id()
      assert my_id != ERROR_TAG, "Failed to get IPFS ID."
      self.P(f"Connecting to relay: {ipfs_relay}")
      result = self.run_command(["ipfs", "swarm", "connect", ipfs_relay])
      if "connect" in result.lower() and "success" in result.lower():
        self.P(f"Connected to relay: {ipfs_relay}", color='g')
        self.__ipfs_started = True
      else:
        self.P("Relay connection result did not indicate success.", color='r')
    except Exception as e:
      self.P(f"Error connecting to relay: {e}", color='r')
      
    return self.ipfs_started
    