import subprocess
import json

class IPFSWrapper:
  def __init__(self, logger=print):
    """
    Initialize the IPFS wrapper with a given logger function.
    By default, it uses the built-in print function for logging.
    """
    self.logger = logger

  def run_command(self, cmd_list):
    """
    Run a shell command using subprocess and return the stdout.
    Also log the command and its result.
    """
    cmd_str = " ".join(cmd_list)
    self.logger(f"Running command: {cmd_str}")
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if result.returncode != 0:
      self.logger(f"Command error: {result.stderr.strip()}")
      raise Exception(f"Error while running '{cmd_str}': {result.stderr.strip()}")
    self.logger(f"Command output: {result.stdout.strip()}")
    return result.stdout.strip()

  def add_file(self, file_path: str) -> str:
    """
    Add a file to IPFS via 'ipfs add -q'.
    Returns the CID of the added file.
    """
    output = self.run_command(["ipfs", "add", "-q", file_path])
    return output  # The CID

  def get_file(self, cid: str, local_filename: str) -> str:
    """
    Get a file from IPFS via 'ipfs get <cid> -o <filename>'.
    Returns the local filename (for convenience).
    """
    self.run_command(["ipfs", "get", cid, "-o", local_filename])
    return local_filename

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
      return data.get("ID", "Unknown")
    except json.JSONDecodeError:
      raise Exception("Failed to parse JSON from 'ipfs id' output.")
