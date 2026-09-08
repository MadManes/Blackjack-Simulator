call .venv\Scripts\activate

pyinstaller --noconfirm --clean --onefile --windowed --name "SimuladorCasino" --icon=assets\icon.ico --add-data "assets/fonts/arial.ttf;assets/fonts" --add-data "assets;assets" --hidden-import pandas --hidden-import matplotlib main.py