docker image rm local_ipfs_test_app
docker image prune -f
docker build \
  --build-arg CACHEBUST=$(date +"%s") \
  -t local_ipfs_test_app \
  -f Dockerfile_app \
  .