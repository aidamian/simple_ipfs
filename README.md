# Simple IPFS Demo (Ratio1 tutorial)

This repository contains a couple containerized applications that demonstrate two ways of interacting with a private IPFS node and exchanging files via a private IPFS swarm. The setup also includes instructions for configuring an IPFS swarm relay. 

---

## 1. Swarm Relay Setup

The swarm relay enables your IPFS node to communicate securely within a private network. Follow these steps to configure and start the relay using the provided bash scripts:

### Step-by-Step Relay Configuration

1. **Generate the Base64-Encoded Swarm Key**  
   Run your key generation script (e.g., `ipfs_keygen`) on your dev machine to produce a file such as `swarm_key_base64.txt`. This file contains your encoded swarm key that secures your private network.

2. **Install Kubo (IPFS Node Manager)**  
   Use the provided `setup.sh` script to download and install Kubo:
   ```bash
   ./setup.sh
   ```
   This script downloads the IPFS binary, extracts it, installs Kubo, initializes the IPFS repository, and configures the node to enable relay hops.
   You should **already** have the `swarm_key_base64.txt` file in the same directory as the `setup.sh` script in order for `write_key.sh` to work - ie the script required to load your base64-encoded swarm key (generated previously on your dev machine) into your IPFS repository. This script decodes the key and writes it to the proper location (e.g., `/root/.ipfs/swarm.key`):
   ```bash
   ./write_key.sh
   ```

3. **Starting the Relay as a Service (Optional)**  
   If you wish to run your IPFS node as a background service, use the `launch_service.sh` script. This script copies the provided systemd service template, reloads the systemd daemon, enables the service, and starts it. Finally, you can view the logs using the `show.sh` script:
   ```bash
   ./launch_service.sh
   ```
   Alternatively, you can run a quick-start relay using the `run.sh` script:
   ```bash
   ./run.sh
   ```

4. **Verify the Relay Setup**  
   After starting the relay, use the command:
   ```bash
   ipfs id
   ```
   to view your node’s details and confirm that the relay address is correctly advertised. You can also check connected peers with:
   ```bash
   ipfs swarm peers
   ```
   > **Note:** You should NOT see any public IPFS peers in the list. If you do, your relay is not properly configured - you are supposed to see only your private swarm peers.

---

## 2. The FastAPI Web App Approach

The first implementation is a web-based application built with FastAPI and Uvicorn. This app provides:

- **File Upload Interface:**  
  A web UI (accessible via a browser) that allows users to upload files, which are then added to IPFS (using the `-w` wrap mode). The generated folder CID is returned and displayed.

- **Manual Pinning:**  
  An endpoint that lets users manually pin a given CID. This is useful if you need to ensure that content is retained by the node.

- **File Listing and Download:**  
  The UI displays all pinned CIDs. When a user clicks on one, the app downloads the corresponding wrapped folder from IPFS and returns the original file.

- **Interactive and User-Friendly:**  
  The front-end is simple yet effective, allowing non-technical users to interact with the IPFS network through standard HTTP requests without any command‑line interaction.

---

## 3. The Standalone Non‑Web App Approach

The second implementation is a non‑web, command‑line based demo that is built around an `IPFSRunner` class. This version is designed for background operation and automated file exchange without a web server. Its key features include:

- **On‑Demand IPFS Startup:**  
  The app waits for a configuration file (named `ifps.ini`) containing the base64‑encoded swarm key and relay address. When the file is present, the app starts the IPFS daemon automatically during its 15‑second polling cycle.

- **Command File Processing:**  
  Every 15 seconds, the app reads a `commands.txt` file for proposed CIDs. It pins each CID, downloads the corresponding wrapped folder from IPFS, and then:
  - Displays the content if the file is text-based (such as `.txt`, `.json`, or `.yaml`).
  - Displays the file size if the file is binary.

- **Status File Generation:**  
  In each cycle, the app generates a status file (randomly in YAML or Pickle format) containing information such as the current timestamp, IPFS peer ID, pinned CIDs, and downloaded files. The status file is added to IPFS, and its resulting CID is recorded, enabling cross-container file exchange.

- **Background Automation:**  
  This approach is ideal for scenarios where the IPFS node must run continuously in the background, automatically processing files and updating status without manual intervention. It also supports integration with external processes by sharing status files through persistent volumes.

---

## Summary

- **Swarm Relay Setup:**  
  Use the provided bash scripts (`setup.sh`, `write_key.sh`, `launch_service.sh`, etc.) to install, configure, and run your IPFS node with a private swarm relay.

- **FastAPI Web App:**  
  Offers a user-friendly web interface for uploading, pinning, listing, and downloading files via IPFS.

- **Standalone Non-Web App:**  
  Runs continuously in the background, automatically processing a command file for CIDs and generating status files. This approach is well‑suited for automated environments where manual web interaction isn’t required.

Choose the approach that best fits your use case: use the FastAPI app if you need a browser-based interface, or the standalone IPFSRunner if you prefer an automated, non‑interactive solution for file exchange in a private IPFS swarm.

Happy experimenting and file sharing!

# Cite
```bibtex
@misc{r1fsbasedemo,
  author = {Andrei Damian},
  title = {Ratio1 - Simple IPFS Demo},
  year = {2025},
  publisher = {GitHub},
  journal = {GitHub repository},
}
```