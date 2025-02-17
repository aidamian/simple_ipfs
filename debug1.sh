docker build -t local_ipfs_test_app -f Dockerfile_app .
docker run --name ipfs_test1_app \
  --rm \
  -v ipfs_1_app:/root/.ipfs  \
  -v ipfs_1_app_data:/app/_local_cache \
  local_ipfs_test_app