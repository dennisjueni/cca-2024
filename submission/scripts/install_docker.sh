#!/bin/bash

if command -v docker &> /dev/null; then
  echo "Docker is installed"
else
    # Add Docker's official GPG key:
    # A try
    echo "\n" | sudo dpkg --configure -a

    sudo apt-get update -y
    sudo apt-get install ca-certificates curl --no-install-recommends -y
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # Add the repository to Apt sources:
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker:
    sudo apt-get update -y
    sudo apt-get install docker-ce docker-ce-cli containerd.io --no-install-recommends -y

    sudo systemctl start docker 
    sudo systemctl enable docker 

fi
