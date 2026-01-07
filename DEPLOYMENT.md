# Deploying Razgon Bot

The 2nd screenshot shows a failed build on GitHub because of the `MetaTrader5` package.

### ⚠️ Critical Requirement: Windows OS
The `MetaTrader5` Python library is **ONLY compatible with Windows**. It does not work on Linux, macOS, or standard GitHub Actions (Ubuntu).

### How to Deploy correctly:
1.  **Windows VPS**: You must use a Windows-based Virtual Private Server (VPS).
2.  **MetaTrader 5 Terminal**: The MT5 terminal must be installed and running on that Windows server.
3.  **No Linux Hosting**: Do not try to host this bot on Heroku, Linux VPS, or Docker (Linux). It will always fail to install the MT5 library.

### Best Workflow:
- Run the bot on your local computer first to test.
- When ready for 24/7 trading, rent a **Windows VPS** (e.g., from providers like FXVM, Chocoping, or standard Windows Server on Azure/AWS).
- Copy the project folder to the Windows VPS and run `python main.py` there.
