# simple_ipfs
Simple containerized app with embedded IPFS node


## Server setup

Generate the base64 encoded IPFS key

```bash
ipfs_keygen
```

copy the `swarm_key_base64.txt` to the target machine then install kubo - the IPFS node manager

```bash
wget https://dist.ipfs.tech/kubo/v0.32.1/kubo_v0.32.1_linux-amd64.tar.gz && \
  tar -xvzf kubo_v0.32.1_linux-amd64.tar.gz && \
  cd kubo && \
  bash install.sh
```


Initialize the IPFS node

```bash
# load the base64 encoded swarm key into the SWARM_KEY_CONTENT_BASE64 env var
cat swarm_key_base64.txt | base64 -d > /root/.ipfs/swarm.key
cat /root/.ipfs/swarm.key
# now we can initialize the IPFS node
ipfs init
```

By default, IPFS can act as a relay if you enable the RelayService in config. For a simple approach, you can do:

```bash
ipfs config --json Swarm.EnableRelayHop true
```

Start the IPFS node

```bash
ipfs daemon
```

### Running as service

Prepare a service file such as `ipfs.service`
```ini
[Unit]
Description=IPFS daemon
After=network.target

[Service]
# Set the user who owns ~/.ipfs (assuming "ipfsuser" owns ~/.ipfs)
User=root
ExecStart=/usr/local/bin/ipfs daemon
Restart=always
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
```

Then run `./setup.sh` or the following commands to enable and start the service

```bash
cp ipfs.service /etc/systemd/system/ipfs.service
sudo systemctl daemon-reload
sudo systemctl enable ipfs
sudo systemctl start ipfs
```

Finally inspect the IPFS logs with:
```bash
# shows the log of the ipfs.service systemd service
journalctl -u ipfs.service -f -n 1000 -a
```

Next, check your IPFS node id

```bash
# check the id of the IPFS node
ipfs id
```

Take the `/ip4/<NODE IP>/tcp/4001/p2p/<PEER ID>` and add it to your client configuration and after starting the clients, check the peers connected to the IPFS node

```bash
# check the peers connected to the IPFS node
ipfs swarm peers
```

