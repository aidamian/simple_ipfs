# simple_ipfs
Simple containerized app with embedded IPFS node


Install kubo - the IPFS node manager

```bash
wget https://dist.ipfs.tech/kubo/v0.32.1/kubo_v0.32.1_linux-amd64.tar.gz && \
  tar -xvzf kubo_v0.32.1_linux-amd64.tar.gz && \
  cd kubo && \
  bash install.sh
```

Initialize the IPFS node

```bash
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