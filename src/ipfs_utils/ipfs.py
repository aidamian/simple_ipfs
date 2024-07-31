import requests
import json

def ipfs_add_file(file_location, IPFS_API_URL, log_info=lambda *args, **kwargs: None):
  # Add file to IPFS using the HTTP API
  with open(file_location, 'rb') as file_data:  # Open the saved file for reading
    files = {'file': file_data}  # Prepare the file for upload
    log_info(f"Adding file to IPFS: {file_location}")
    response = requests.post(f"{IPFS_API_URL}/add", files=files)  # Add the file to IPFS
    response.raise_for_status()  # Raise an error if the request was not successful
    json_data = response.json()  # Parse the JSON response

  # Extract CID from the IPFS output
  cid = json_data["Hash"]  # Get the CID from the response
  return cid


def ipfs_list_mutable_files(IPFS_API_URL, log_info=lambda *args, **kwargs: None):
  url = f"{IPFS_API_URL}/files/ls"  # Prepare the URL to list files in IPFS
  log_info(f"Retrieving mutable files from {url}")
  response = requests.post(url)  # List files in IPFS
  response.raise_for_status()  # Raise an error if the request was not successful
  dct_data = response.json()
  files = dct_data["Entries"]  # Get the file entries from the response
  log_info(f"Received from IPFS: {json.dumps(dct_data, indent=2)}")
  return files


def ipfs_list_pin_files(IPFS_API_URL, log_info=lambda *args, **kwargs: None):
  url = f"{IPFS_API_URL}/pin/ls"  # Prepare the URL to list files in IPFS
  log_info(f"Retrieving pinned files from {url}")
  response = requests.post(url)  # List files in IPFS
  response.raise_for_status()  # Raise an error if the request was not successful
  dct_data = response.json()
  files = None
  log_info(f"Received from IPFS: {json.dumps(dct_data, indent=2)}")
  try:
    files = list(dct_data["Keys"].keys())  # Get the file entries from the response
  except Exception as e:
    log_info(f"Error parsing response: {str(e)}", color='r')
  return files


def ipfs_get_id(IPFS_API_URL):
  """Retrieve the IPFS peer ID."""
  try:
    # Fetch the peer ID from the IPFS node
    response = requests.post(f"{IPFS_API_URL}/id")
    response.raise_for_status()
    peer_info = response.json()
    peer_id = peer_info["ID"]
  except Exception as e:
    peer_id = "Unavailable: " + str(e)
  return peer_id


