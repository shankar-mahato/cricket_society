# 🚀 Create Web App on PythonAnywhere

## The Issue
You don't have a web app created yet on PythonAnywhere. You need to create one first before you can deploy.

## Step-by-Step: Create Your Web App

### Step 1: Log in to PythonAnywhere
1. Go to: https://www.pythonanywhere.com/
2. Log in with username: `cricketsociety`

### Step 2: Create New Web App
1. Click on **"Web"** tab in the top menu
2. Click **"Add a new web app"** button
3. If prompted, click **"Next"** on the domain selection (use default)

### Step 3: Choose Configuration
1. Select **"Manual configuration"** (not "Flask" or "Django")
2. Select **Python 3.10** (or the latest available version)
3. Click **"Next"**

### Step 4: Complete Setup
1. The web app will be created
2. **Note the web app name** - it's usually your username (`cricketsociety`) or you can set a custom name
3. You'll see the web app in your list

### Step 5: Update deploy.py
Once you know the web app name, update `deploy.py`:

```python
webapp_name = 'cricketsociety'  # Or whatever name was created
```

### Step 6: Configure WSGI File
1. In the **Web** tab, click on your web app
2. Click **"WSGI configuration file"** link
3. Replace the content with:

```python
import os
import sys

path = '/home/cricketsociety/cricket_society/mycricket'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'mycricket.settings'

activate_this = '/home/cricketsociety/cricket_society/venv/bin/activate_this.py'
if os.path.exists(activate_this):
    with open(activate_this) as f:
        exec(f.read(), {'__file__': activate_this})

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Step 7: Set Up Static Files
1. In **Web** tab → **Static files** section
2. Add:
   - URL: `/static/` → Directory: `/home/cricketsociety/cricket_society/mycricket/staticfiles/`
   - URL: `/media/` → Directory: `/home/cricketsociety/cricket_society/mycricket/media/`

### Step 8: Clone Repository (if not done)
1. Go to **Files** tab → Open **Bash console**
2. Run:
```bash
cd ~
git clone https://github.com/shankar-mahato/cricket_society.git
cd cricket_society
python3.10 -m venv venv
source venv/bin/activate
cd mycricket
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

### Step 9: Reload Web App
1. Go back to **Web** tab
2. Click **"Reload"** button

### Step 10: Test deploy.py
Now run:
```bash
python deploy.py
```

It should work! ✅

---

## Quick Checklist

- [ ] Web app created on PythonAnywhere
- [ ] Web app name noted
- [ ] `webapp_name` updated in deploy.py
- [ ] Repository cloned on PythonAnywhere
- [ ] Virtual environment set up
- [ ] WSGI file configured
- [ ] Static files configured
- [ ] Migrations run
- [ ] Web app reloaded
- [ ] deploy.py tested

---

## Common Web App Names

After creation, your web app name will typically be:
- `cricketsociety` (same as username - most common)
- Or a custom name you chose during setup

Run `python deploy.py` after creating the web app to see the exact name!

