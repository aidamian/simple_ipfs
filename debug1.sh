docker build -t local_ipfs_test .
docker run --name ipfs_test1 --rm -p 8001:8000 --env-file=.env -v ipfs_1:/root/.ipfs local_ipfs_test