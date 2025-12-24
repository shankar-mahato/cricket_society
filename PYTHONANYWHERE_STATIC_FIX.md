# Fixing collectstatic Error on PythonAnywhere

## Problem
The `collectstatic` command fails with a file existence check error, usually due to:
1. STATIC_ROOT directory doesn't exist
2. Permission issues
3. STATIC_ROOT path not properly configured

## Solution

### Step 1: Create Static Files Directory

SSH into PythonAnywhere and run:

```bash
cd /home/cricketsociety/cricket_society/mycricket
mkdir -p staticfiles
chmod 755 staticfiles
```

### Step 2: Verify STATIC_ROOT in settings.py

Make sure your `settings.py` has:

```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

### Step 3: Run collectstatic with proper path

```bash
cd /home/cricketsociety/cricket_society/mycricket
source ../venv/bin/activate
python manage.py collectstatic --noinput
```

The `--noinput` flag automatically answers "yes" to the prompt.

### Step 4: Configure Static Files in PythonAnywhere Web App

1. Go to PythonAnywhere Dashboard → Web tab
2. Click on your web app
3. Scroll down to "Static files" section
4. Add a mapping:
   - **URL**: `/static/`
   - **Directory**: `/home/cricketsociety/cricket_society/mycricket/staticfiles`

### Step 5: Configure Media Files (for user uploads)

Also add a mapping for media files:
- **URL**: `/media/`
- **Directory**: `/home/cricketsociety/cricket_society/mycricket/media`

### Alternative: If using project root

If your project structure is different and `manage.py` is in `/home/cricketsociety/cricket_society/`, then:

```bash
cd /home/cricketsociety/cricket_society
mkdir -p staticfiles
chmod 755 staticfiles
python mycricket/manage.py collectstatic --noinput
```

And update the static files directory path in PythonAnywhere to:
- `/home/cricketsociety/cricket_society/staticfiles`

## Troubleshooting

### Permission Denied Error

If you get permission errors:
```bash
chmod -R 755 /home/cricketsociety/cricket_society/mycricket/staticfiles
chmod -R 755 /home/cricketsociety/cricket_society/mycricket/media
```

### Directory Doesn't Exist Error

Make sure the directory exists before running collectstatic:
```bash
mkdir -p staticfiles media
```

### Check Current STATIC_ROOT

To verify your STATIC_ROOT setting:
```bash
python manage.py shell
>>> from django.conf import settings
>>> print(settings.STATIC_ROOT)
```




