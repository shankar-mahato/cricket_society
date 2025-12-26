# 🔧 Fix WSGI Configuration Error

## The Problem
The error `ModuleNotFoundError: No module named 'cricketsociety'` means your WSGI file is trying to import the wrong module name.

Your Django project is named `mycricket`, not `cricketsociety`.

## Solution: Update WSGI File

### Step 1: Go to WSGI Configuration
1. Log in to PythonAnywhere
2. Go to **Web** tab
3. Click on your web app: `cricketsociety.pythonanywhere.com`
4. Click **"WSGI configuration file"** link

### Step 2: Replace the WSGI File Content

Replace **ALL** content in the WSGI file with this:

```python
import os
import sys

# Add your project directory to the Python path
path = '/home/cricketsociety/cricket_society/mycricket'
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'mycricket.settings'

# Activate virtual environment
activate_this = '/home/cricketsociety/cricket_society/venv/bin/activate_this.py'
if os.path.exists(activate_this):
    with open(activate_this) as f:
        exec(f.read(), {'__file__': activate_this})

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Step 3: Save and Reload
1. Click **"Save"** button
2. Go back to **Web** tab
3. Click **"Reload"** button (green button)

### Step 4: Check Error Log
If there are still errors:
1. Go to **Web** tab
2. Click **"Error log"** link
3. Check for any new errors

---

## Key Points

✅ **Correct settings module**: `mycricket.settings` (not `cricketsociety.settings`)
✅ **Correct path**: `/home/cricketsociety/cricket_society/mycricket`
✅ **Virtual environment**: `/home/cricketsociety/cricket_society/venv`

---

## After Fixing

Your site should work at: **https://cricketsociety.pythonanywhere.com**

If you still see errors, check:
1. Virtual environment path is correct
2. Project path is correct
3. All dependencies are installed in venv
4. Static files are configured

