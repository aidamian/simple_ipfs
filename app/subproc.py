from time import sleep

from ratio1.ipfs import R1FSEngine

LOCAL_CACHE = '_local_cache'

def main_loop(log):
  r1fs = R1FSEngine(logger=log, debug=True)
  # Simulate some work
  while True:    
    peers = r1fs._get_swarm_peers()
    log.P(f"[SUBPROC] {r1fs.ipfs_id} has {len(peers)} peers", color='m')
    sleep(5)
  return

if __name__ == "__main__":
  from ratio1 import Logger
  
  log = Logger("R1FS_SUB", base_folder=".", app_folder=LOCAL_CACHE)
  main_loop(log=log)