#!/bin/bash
# -----------------------------------------------------------------------------
# MedMentor AWS EC2 One-Click Deployment Script
# Run this inside your fresh Ubuntu EC2 instance to configure Docker, 
# clone the repo, set up environment keys, and start the container.
# -----------------------------------------------------------------------------

# Exit on error
set -e

echo "🚀 Starting MedMentor setup on AWS EC2..."

# 1. Update system package index
echo "⚙️ Updating system packages..."
sudo apt-get update -y

# 2. Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    sudo apt-get install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    # Add current user to docker group to avoid typing 'sudo' for docker commands
    sudo usermod -aG docker $USER
    echo "✅ Docker installed successfully!"
else
    echo "🐳 Docker is already installed."
fi

# 3. Create .env file template if it doesn't exist
if [ ! -f .env ]; then
    echo "🔑 Creating .env template file..."
    cat <<EOT > .env
GROQ_API_KEY=your_groq_api_key_here
SARVAM_API_KEY=your_sarvam_api_key_here
EOT
    echo "⚠️  Created .env file. Please edit this file to insert your actual API keys using: nano .env"
fi

# 4. Build Docker Image
echo "🏗️  Building MedMentor Docker container..."
docker build -t medmentor .

# 5. Run Docker Container
echo "🏃 Starting MedMentor on port 8000..."
# Stop existing container if running
docker stop medmentor-instance &>/dev/null || true
docker rm medmentor-instance &>/dev/null || true

# Run new container
docker run -d \
  --name medmentor-instance \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  medmentor

echo "🎉 Deployment successful!"
echo "--------------------------------------------------------"
echo "MedMentor is running on: http://your-ec2-ip:8000/app"
echo "Check logs using: docker logs -f medmentor-instance"
echo "--------------------------------------------------------"
