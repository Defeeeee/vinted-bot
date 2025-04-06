@echo off

echo Creating Python virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo Installing playwright...
python -m playwright install

set /p token=Please enter your DISCORD_BOT_TOKEN: 
echo DISCORD_BOT_TOKEN=%token%> .env

echo Running the bot...
python main.py

