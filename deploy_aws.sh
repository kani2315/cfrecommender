#!/bin/bash
# AWS EC2 User-Data Script for Codeforces Recommender Deployment
#
# Usage:
# 1. Launch an Amazon Linux 2023 EC2 instance (t3.small or larger recommended).
# 2. Paste this script into the "User data" section during launch.
# 3. The server will automatically install Docker, pull your code (if public), and start the services.

# Update system
sudo yum update -y

# Install Docker & Git
sudo yum install -y docker git
sudo service docker start
sudo usermod -a -G docker ec2-user
sudo systemctl enable docker

# Install Docker Compose (v2)
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Create app directory and clone repository
cd /home/ec2-user
git clone https://github.com/kani2315/cfrecommender.git
cd cfrecommender

# Start the full stack (Database, FastAPI Server, and Scheduler)
docker compose up --build -d

echo "Deployment complete! Application should be accessible on port 8000."
