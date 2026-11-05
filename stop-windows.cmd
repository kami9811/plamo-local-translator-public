@echo off
if not defined PLAMO_REPO (
  echo Set PLAMO_REPO to the absolute Linux checkout path. See docs/SETUP.md.
  exit /b 1
)
if defined PLAMO_WSL_DISTRO (
  wsl.exe -d "%PLAMO_WSL_DISTRO%" --cd "%PLAMO_REPO%" python3 scripts/stop.py
) else (
  wsl.exe --cd "%PLAMO_REPO%" python3 scripts/stop.py
)
