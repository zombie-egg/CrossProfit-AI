@echo off
cd /d %~dp0
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe run_streamlit.py
) else (
  python run_streamlit.py
)
