# 🚀 Quick Deployment Steps

## Step 1: Push to GitHub

```bash
cd /Users/shankar.mahato/DemoCricketAPP

# Add all changes
git add .

# Commit
git commit -m "Update: Redesign navbar, rename to CricketSociety, integrate Odds API"

# Push to GitHub
git push origin main
```

## Step 2: Set Up PythonAnywhere (First Time Only)

### 2.1 Initial Setup
1. Go to https://www.pythonanywhere.com/ and sign up/login
2. Go to **Web** tab → **Add a new web app**
3. Choose **Manual configuration** → **Python 3.10**
4. Click **Next** until created

### 2.2 Clone Repository
1. Go to **Files** tab → Open **Bash console**
2. Run:
```bash
cd ~
git clone https://github.com/shankar-mahato/cricket_society.git
cd cricket_society
```

### 2.3 Set Up Virtual Environment
```bash
python3.10 -m venv venv
source venv/bin/activate
cd mycricket
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 Configure WSGI
1. Go to **Web** tab → Click **WSGI configuration file**
2. Replace content with:
```python
import os
import sys

path = '/home/YOUR_USERNAME/cricket_society/mycricket'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'mycricket.settings'

activate_this = '/home/YOUR_USERNAME/cricket_society/venv/bin/activate_this.py'
if os.path.exists(activate_this):
    with open(activate_this) as f:
        exec(f.read(), {'__file__': activate_this})

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
**Replace `YOUR_USERNAME` with your PythonAnywhere username**

### 2.5 Set Up Static Files
1. In Bash console:
```bash
cd ~/cricket_society/mycricket
source ../venv/bin/activate
python manage.py collectstatic --noinput
```

2. In **Web** tab → **Static files**, add:
   - URL: `/static/` → Directory: `/home/YOUR_USERNAME/cricket_society/mycricket/staticfiles/`
   - URL: `/media/` → Directory: `/home/YOUR_USERNAME/cricket_society/mycricket/media/`

### 2.6 Run Migrations
```bash
cd ~/cricket_society/mycricket
source ../venv/bin/activate
python manage.py migrate
python manage.py createsuperuser  # Optional
```

### 2.7 Update Settings
Edit `mycricket/settings.py`:
```python
ALLOWED_HOSTS = ['YOUR_USERNAME.pythonanywhere.com']
DEBUG = False  # For production
```

### 2.8 Reload Web App
Click **Reload** button in **Web** tab

---

## Step 3: Automatic Deployment (After First Setup)

### 3.1 Get API Token
1. Go to: https://www.pythonanywhere.com/user/YOUR_USERNAME/api_token/
2. Copy your API token

### 3.2 Update deploy.py
Edit `deploy.py` in your repository:
```python
USERNAME = 'your_pythonanywhere_username'
WEBAPP_NAME = 'your_webapp_name'  # Usually same as username
API_TOKEN = 'your_api_token_here'
```

### 3.3 Deploy After Each Push
After pushing to GitHub, run:
```bash
python deploy.py
```

Or manually:
1. SSH into PythonAnywhere
2. Run:
```bash
cd ~/cricket_society
git pull origin main
source venv/bin/activate
cd mycricket
python manage.py collectstatic --noinput
python manage.py migrate
```
3. Go to **Web** tab → Click **Reload**

---

## Step 4: Set Up Daily Match Sync

1. Go to **Tasks** tab in PythonAnywhere
2. Click **Create a new task**
3. Set:
   - **Command**: `cd ~/cricket_society/mycricket && source ../venv/bin/activate && python manage.py sync_matches --api odds`
   - **Hour**: `0` (midnight)
   - **Minute**: `0`
   - **Enabled**: ✓

---

## ✅ Quick Checklist

- [ ] Code pushed to GitHub
- [ ] PythonAnywhere web app created
- [ ] Repository cloned
- [ ] Virtual environment set up
- [ ] Dependencies installed
- [ ] WSGI configured
- [ ] Static files collected
- [ ] Migrations run
- [ ] Settings updated (ALLOWED_HOSTS, DEBUG)
- [ ] Web app reloaded
- [ ] Site tested

---

## 🔗 Your Site URL

After setup, your site will be live at:
**https://YOUR_USERNAME.pythonanywhere.com**

---

## 📝 Notes

- Free tier allows 1 web app
- Free tier has limited CPU time
- Database is SQLite (sufficient for small apps)
- Static files need to be collected after each deployment
- Always test locally before deploying

