#!/bin/bash

for var in "$@"
do
	sshpass -p stack ssh -f -L 11111:172.31.0.2:22 stack@198.101.133.84 sleep 120
	scp -i alamoaio.pem -P 11111 \./${var} ubuntu@localhost:
done

for var in "$@"
do
	sshpass -p stack ssh -f -L 11111:172.31.0.2:22 stack@198.101.133.84 sleep 120
	sshpass -i alamoaio.pem ssh -f -L 22222:localhost:22 ubuntu@localhost
	sudo cp ${var} /opt/rpcs
done