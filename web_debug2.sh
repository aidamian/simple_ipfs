docker build -t local_ipfs_test_web -f Dockerfile_web .
docker run --name ipfs_test2_web --rm -p 8002:8000 \--env-file=.env 
  -v ipfs_2_web:/root/.ipfs 
  local_ipfs_test_web