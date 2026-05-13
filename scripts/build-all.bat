@echo off
cd /d "%~dp0.."
echo === Building frontend ===
cd frontend
call npx astro build
if %errorlevel% neq 0 exit /b %errorlevel%
cd ..
echo === Building docs ===
python -m mkdocs build -f docs/mkdocs.yml --site-dir "%CD%\server\static\docs"
if %errorlevel% neq 0 exit /b %errorlevel%
echo === Done ===
