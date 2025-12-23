# PythonAnywhere WSGI Configuration

## Problem
The error `ModuleNotFoundError: No module named 'mycricket'` occurs because the WSGI file doesn't have the correct path configuration.

## Solution

### Step 1: Edit WSGI File on PythonAnywhere

1. Go to PythonAnywhere Dashboard
2. Click on "Web" tab
3. Click on your web app (cricketsociety.pythonanywhere.com)
4. Click on "WSGI configuration file" link
5. Replace the entire content with the configuration below

### Step 2: WSGI Configuration

Replace the WSGI file content with this:

```python
# +++++++++++ DJANGO +++++++++++
# To use your own Django app use code like this:
import os
import sys

# Add your project directory to the Python path
project_home = '/home/cricketsociety/cricket_society'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Add the mycricket directory to the Python path
mycricket_path = '/home/cricketsociety/cricket_society/mycricket'
if mycricket_path not in sys.path:
    sys.path.insert(0, mycricket_path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'mycricket.settings'

# Change to the project directory
os.chdir(project_home)

# Then:
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Step 3: Update Paths

**IMPORTANT:** Update these paths in the WSGI file to match your actual setup:

- `/home/cricketsociety/cricket_society` → Your actual project root path
- `/home/cricketsociety/cricket_society/mycricket` → Your actual Django project path (where manage.py is)

### Step 4: Verify Project Structure

Your project structure on PythonAnywhere should be:

```
/home/cricketsociety/cricket_society/
├── mycricket/
│   ├── manage.py
│   ├── mycricket/
│   │   ├── settings.py
│   │   ├── wsgi.py
│   │   └── urls.py
│   ├── accounts/
│   ├── core/
│   └── ...
├── requirements.txt
├── .git/
└── venv/
```

### Step 5: Reload Web App

After saving the WSGI file:
1. Click the green "Reload" button in the Web tab
2. Check the error log to see if the issue is resolved

## Alternative: If Project is in Root Directory

If your `mycricket` folder is directly in `/home/cricketsociety/`, use this configuration:

```python
import os
import sys

# Add your project directory to the Python path
project_home = '/home/cricketsociety'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Add the mycricket directory to the Python path
mycricket_path = '/home/cricketsociety/mycricket'
if mycricket_path not in sys.path:
    sys.path.insert(0, mycricket_path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'mycricket.settings'

# Change to the project directory
os.chdir(mycricket_path)

# Then:
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## Troubleshooting

### Check Current Paths

SSH into PythonAnywhere and check your actual paths:

```bash
ssh cricketsociety@ssh.pythonanywhere.com
pwd
ls -la
find . -name "manage.py" -type f
```

### Verify Settings Module

Make sure `DJANGO_SETTINGS_MODULE` matches your actual settings file location:
- If settings.py is at `/home/cricketsociety/cricket_society/mycricket/mycricket/settings.py`
- Then use: `os.environ['DJANGO_SETTINGS_MODULE'] = 'mycricket.settings'`

### Check Virtual Environment

Make sure your virtual environment is activated and has Django installed:

```bash
source venv/bin/activate
python -c "import django; print(django.get_version())"
```

### Test Import Manually

Test if you can import the module:

```bash
cd /home/cricketsociety/cricket_society/mycricket
python
>>> import sys
>>> sys.path.insert(0, '/home/cricketsociety/cricket_society/mycricket')
>>> from mycricket.settings import *
```

If this works, use the same paths in your WSGI file.

