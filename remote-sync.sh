#!/bin/bash

rsync -avz -e "ssh -i ~/.ssh/backend_vm_key_pair.pem" \
/Users/abhishakebojja/Dev/projects/network_analysis/ \
talker25@172.178.38.117:~/projects/network_analysis/