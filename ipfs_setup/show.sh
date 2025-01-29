# shows the log of the ipfs.service systemd service
journalctl -u ipfs.service -f -n 1000 -a