#!/bin/bash

FILE_PATH="app/bot.py"

if pgrep -f $FILE_PATH >/dev/null; then
    echo "Python process $FILE_PATH is already running. Please run 'bash app/stop.sh' first to start the bot again."
else
    echo "Python process $FILE_PATH is not running."
    echo "Starting ChatGPT Discord Bot..."
    source bin/activate
    python3 app/bot.py
fi