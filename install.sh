#!/bin/bash

echo "Creating Python virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Installing playwright..."
python -m playwright install

read -p "Please enter your DISCORD_BOT_TOKEN: " token
echo "DISCORD_BOT_TOKEN=$token" > .env

echo "Running the bot..."
python main.py
