docker run --name ipfs_test2_app \
  --rm \
  -e SUBPROC=0 \
  -v ipfs_2_app_data:/app/_local_cache \
  local_ipfs_test_app