#!bin/bash

git pull origin master

touch app/keys.json

echo "Building Python Environment..."
pip install virtualenv

# install requirements
virtualenv -p /usr/bin/python3 chatgpt-discord-bot
pip install -r requirements.txt





