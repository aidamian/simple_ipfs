docker build -t local_ipfs_test_web -f Dockerfile_web .
docker run --name ipfs_test1_web --rm -p 8001:8000 --env-file=.env local_ipfs_test_web