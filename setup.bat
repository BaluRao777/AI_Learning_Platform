@echo off
REM Windows launcher: finds Python 3.10-3.13 and runs setup_project.py.
REM   setup.bat            (interactive)
REM   setup.bat --help     (options)
cd /d "%~dp0"
echo Detected OS: Windows
for %%V in (3.11 3.12 3.10 3.13) do (
  py -%%V -c "import sys" >nul 2>&1 && (
    echo Using Python %%V
    py -%%V setup_project.py %*
    goto :end
  )
)
python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>&1 && (
  echo Using python from PATH
  python setup_project.py %*
  goto :end
)
echo ERROR: Python 3.10 - 3.13 was not found.
echo Install Python 3.11 from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
:end
pause
