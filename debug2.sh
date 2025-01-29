docker build -t local_ipfs_test .
docker run -n ipfs_test2 --rm -p 8002:8000 --env-file=.env -v ipfs_2:/root/.ipfs local_ipfs_test