# 🚀 How to Run deploy.py

## The Problem
You're trying to run `deploy.py` from the wrong directory. The file is in the root directory (`DemoCricketAPP`), not in `mycricket`.

## Solution

### Option 1: Navigate to the correct directory first
```bash
# Go back to the project root
cd /Users/shankar.mahato/DemoCricketAPP

# Then run the script
python deploy.py
```

### Option 2: Run from anywhere (using full path)
```bash
python /Users/shankar.mahato/DemoCricketAPP/deploy.py
```

### Option 3: If requests module is missing
If you get `ModuleNotFoundError: No module named 'requests'`, install it:

```bash
# Activate your virtual environment first
cd /Users/shankar.mahato/DemoCricketAPP
source venv/bin/activate  # or: . venv/bin/activate

# Install requests
pip install requests

# Then run deploy
python deploy.py
```

## Quick Command (Copy & Paste)
```bash
cd /Users/shankar.mahato/DemoCricketAPP && python deploy.py
```

## What the script does
1. Connects to PythonAnywhere API
2. Reloads your web app automatically
3. Shows success/error message

## After running successfully
You should see:
```
🚀 Deploying to PythonAnywhere...
✅ Web app reloaded successfully!
   Visit: https://cricketsociety.pythonanywhere.com
```

Then visit your site to see the changes!

