@echo off
:: Create virtual environment if it doesn't exist
if not exist .venv (
    echo Creating virtual environment .venv...
    python -m venv .venv
)

:: Activate the virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate

:: Install required python packages
echo Installing dependencies...
pip install -r requirements.txt

:: Run the application
echo Starting the Student Portal...
python wsgi.py

pause
