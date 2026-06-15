@echo off
echo Starting local server for the Map...
echo Please wait while your default browser opens.
start http://localhost:8000/map.html
python -m http.server 8000
