#!/bin/bash
echo "Starting admin bot..."
python3 admin_bot.py &
echo "Starting main bot..."
python3 bot.py
