:: build:env.bat
py -m venv .venv
call .venv\Scripts\activate
pip install --upgrade pip
pip install pyinstaller pygame 
pip install pandas matplotlib