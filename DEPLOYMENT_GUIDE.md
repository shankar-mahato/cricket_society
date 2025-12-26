# 🚀 Deployment Guide: GitHub to PythonAnywhere

This guide will help you push your code to GitHub and set up automatic deployment to PythonAnywhere.

## 📋 Prerequisites

1. GitHub account
2. PythonAnywhere account (free tier works)
3. Git installed on your local machine

---

## Step 1: Push Code to GitHub

### 1.1 Check Current Status
```bash
cd /Users/shankar.mahato/DemoCricketAPP
git status
```

### 1.2 Add All Changes
```bash
# Add all modified and new files
git add .

# Or add specific files
git add mycricket/
git add *.md
```

### 1.3 Commit Changes
```bash
git commit -m "Update UI: Redesign navbar, rename to CricketSociety, integrate Odds API"
```

### 1.4 Push to GitHub
```bash
# If you haven't set up remote yet:
# git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git push origin main

# If you're on a different branch:
# git push origin YOUR_BRANCH_NAME
```

---

## Step 2: Set Up PythonAnywhere Account

### 2.1 Create PythonAnywhere Account
1. Go to https://www.pythonanywhere.com/
2. Sign up for a free account
3. Verify your email

### 2.2 Get Your API Token
1. Go to https://www.pythonanywhere.com/user/YOUR_USERNAME/api_token/
2. Copy your API token (you'll need this for automatic deployment)

---

## Step 3: Configure PythonAnywhere Web App

### 3.1 Create New Web App
1. Go to **Web** tab in PythonAnywhere dashboard
2. Click **Add a new web app**
3. Choose **Manual configuration**
4. Select **Python 3.10** (or latest available)
5. Click **Next** until web app is created

### 3.2 Clone Your Repository
1. Go to **Files** tab
2. Open **Bash console**
3. Navigate to your home directory:
   ```bash
   cd ~
   ```
4. Clone your GitHub repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   ```
   Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub details.

---

## Step 4: Set Up Virtual Environment

### 4.1 Create Virtual Environment
```bash
cd ~/YOUR_REPO_NAME
python3.10 -m venv venv
source venv/bin/activate
```

### 4.2 Install Dependencies
```bash
cd mycricket
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 5: Configure WSGI File

### 5.1 Edit WSGI File
1. Go to **Web** tab
2. Click on **WSGI configuration file** link
3. Replace the content with:

```python
import os
import sys

# Add your project directory to the path
path = '/home/YOUR_USERNAME/YOUR_REPO_NAME/mycricket'
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'mycricket.settings'

# Activate virtual environment
activate_this = '/home/YOUR_USERNAME/YOUR_REPO_NAME/venv/bin/activate_this.py'
if os.path.exists(activate_this):
    with open(activate_this) as f:
        exec(f.read(), {'__file__': activate_this})

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Important:** Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual values.

---

## Step 6: Configure Static Files

### 6.1 Collect Static Files
In the Bash console:
```bash
cd ~/YOUR_REPO_NAME/mycricket
source ../venv/bin/activate
python manage.py collectstatic --noinput
```

### 6.2 Set Static Files Mapping
1. Go to **Web** tab
2. Scroll to **Static files** section
3. Add these mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/YOUR_USERNAME/YOUR_REPO_NAME/mycricket/staticfiles/` |
| `/media/` | `/home/YOUR_USERNAME/YOUR_REPO_NAME/mycricket/media/` |

---

## Step 7: Set Up Database

### 7.1 Run Migrations
```bash
cd ~/YOUR_REPO_NAME/mycricket
source ../venv/bin/activate
python manage.py migrate
```

### 7.2 Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

---

## Step 8: Configure Environment Variables

### 8.1 Set Secret Key
1. Go to **Web** tab
2. Click **Environment variables**
3. Add:
   - `SECRET_KEY`: Your Django secret key
   - `DEBUG`: `False` (for production)
   - `ALLOWED_HOSTS`: `yourusername.pythonanywhere.com`

Or edit `mycricket/settings.py` directly:
```python
import os
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']
```

---

## Step 9: Automatic Deployment Setup

### Option A: Using PythonAnywhere API (Recommended)

#### 9.1 Create Deployment Script
Create a file `deploy.sh` in your repository:

```bash
#!/bin/bash
# deploy.sh - Automatic deployment script

cd ~/YOUR_REPO_NAME
git pull origin main

source venv/bin/activate
cd mycricket

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# Reload web app
curl -X POST https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/webapps/YOUR_WEBAPP_NAME/reload/ \
    -H "Authorization: Token YOUR_API_TOKEN"
```

#### 9.2 Make Script Executable
```bash
chmod +x deploy.sh
```

#### 9.3 Set Up GitHub Webhook (Advanced)
1. Go to your GitHub repository
2. Go to **Settings** → **Webhooks**
3. Add webhook:
   - Payload URL: `https://YOUR_USERNAME.pythonanywhere.com/webhook/` (you'll need to create this endpoint)
   - Content type: `application/json`
   - Events: `Just the push event`

### Option B: Manual Reload (Simple)

After pushing to GitHub, manually reload:
1. SSH into PythonAnywhere
2. Run:
   ```bash
   cd ~/YOUR_REPO_NAME
   git pull origin main
   source venv/bin/activate
   cd mycricket
   python manage.py collectstatic --noinput
   python manage.py migrate
   ```
3. Go to **Web** tab and click **Reload**

---

## Step 10: Set Up Scheduled Tasks (Optional)

### 10.1 Sync Matches Automatically
1. Go to **Tasks** tab
2. Click **Create a new task**
3. Set:
   - **Command**: `cd ~/YOUR_REPO_NAME/mycricket && source ../venv/bin/activate && python manage.py sync_matches --api odds`
   - **Hour**: `0` (midnight)
   - **Minute**: `0`
   - **Enabled**: ✓

This will sync matches daily at midnight.

---

## Step 11: Test Your Deployment

1. Go to **Web** tab
2. Click **Reload** button
3. Visit your site: `https://YOUR_USERNAME.pythonanywhere.com`
4. Test all features:
   - User registration/login
   - Match viewing
   - Session creation
   - Betting functionality

---

## 🔄 Automatic Deployment Workflow

### Quick Deploy Script

Create `deploy.py` in your repository root:

```python
#!/usr/bin/env python3
"""
Automatic deployment script for PythonAnywhere
Run this after pushing to GitHub
"""
import requests
import os

USERNAME = 'YOUR_USERNAME'
WEBAPP_NAME = 'YOUR_WEBAPP_NAME'  # Usually same as username
API_TOKEN = 'YOUR_API_TOKEN'

def reload_webapp():
    """Reload PythonAnywhere web app"""
    url = f'https://www.pythonanywhere.com/api/v0/user/{USERNAME}/webapps/{WEBAPP_NAME}/reload/'
    headers = {'Authorization': f'Token {API_TOKEN}'}
    
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        print('✅ Web app reloaded successfully!')
    else:
        print(f'❌ Error: {response.status_code} - {response.text}')

if __name__ == '__main__':
    reload_webapp()
```

### Usage:
```bash
# After pushing to GitHub
python deploy.py
```

---

## 📝 Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] PythonAnywhere account created
- [ ] Web app created
- [ ] Repository cloned on PythonAnywhere
- [ ] Virtual environment set up
- [ ] Dependencies installed
- [ ] WSGI file configured
- [ ] Static files collected
- [ ] Database migrations run
- [ ] Environment variables set
- [ ] Web app reloaded
- [ ] Site tested and working

---

## 🐛 Troubleshooting

### Issue: 500 Internal Server Error
- Check error logs in **Web** tab → **Error log**
- Verify WSGI configuration
- Check database migrations

### Issue: Static files not loading
- Verify static files mapping in **Web** tab
- Run `collectstatic` again
- Check file permissions

### Issue: Module not found
- Verify virtual environment is activated
- Check `requirements.txt` has all dependencies
- Verify Python version matches

### Issue: Database errors
- Run migrations: `python manage.py migrate`
- Check database file permissions
- Verify database path in settings

---

## 🔐 Security Notes

1. **Never commit sensitive data:**
   - Secret keys
   - API keys
   - Database passwords
   - Use environment variables instead

2. **Update .gitignore:**
   - Ensure `.env` files are ignored
   - Ignore `db.sqlite3` in production
   - Ignore `__pycache__` directories

3. **Set DEBUG=False in production:**
   ```python
   DEBUG = os.environ.get('DEBUG', 'False') == 'True'
   ```

---

## 📚 Additional Resources

- [PythonAnywhere Help](https://help.pythonanywhere.com/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [PythonAnywhere API Docs](https://www.pythonanywhere.com/api/)

---

## 🎉 You're Done!

Your app should now be live at: `https://YOUR_USERNAME.pythonanywhere.com`

For automatic deployment, after each `git push`, run the deploy script or manually reload the web app.

