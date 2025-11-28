#!/bin/bash
# Setup script for Python virtual environment

echo "Setting up Python virtual environment..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

echo "Virtual environment setup complete!"
echo "To activate the virtual environment, run: source api_backend/venv/bin/activate"
