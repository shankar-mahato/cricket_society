# Deployment Guide for CricketDuel

This guide will help you deploy the CricketDuel Django application to PythonAnywhere (free tier).

## Prerequisites

1. A PythonAnywhere account (sign up at https://www.pythonanywhere.com/)
2. Git repository (GitHub, GitLab, or Bitbucket)
3. Your Django project code

## Pre-Deployment Checklist

### 1. Install Required Dependencies

Before deploying, ensure you have Pillow installed for image handling:

```bash
pip install Pillow
```

### 2. Update Settings for Production

Create a `production_settings.py` or update `settings.py`:

```python
# In mycricket/mycricket/settings.py, update for production:

DEBUG = False
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']  # Replace with your PythonAnywhere username

# Database - PythonAnywhere provides MySQL/PostgreSQL on paid plans
# For free tier, SQLite works but consider upgrading for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = '/home/yourusername/mysite/static'  # Update path

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = '/home/yourusername/mysite/media'  # Update path

# Security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 3. Create requirements.txt

```bash
pip freeze > requirements.txt
```

Your `requirements.txt` should include:
```
Django>=5.2,<6.0
Pillow>=10.0.0
requests>=2.31.0
```

## PythonAnywhere Deployment Steps

### Step 1: Upload Your Code

**Option A: Using Git (Recommended)**
1. Push your code to GitHub/GitLab/Bitbucket
2. In PythonAnywhere Dashboard → Files tab
3. Open a Bash console
4. Run:
```bash
cd ~
git clone https://github.com/yourusername/your-repo.git
cd your-repo
```

**Option B: Using Files Tab**
1. Go to Files tab in PythonAnywhere
2. Upload files manually (not recommended for large projects)

### Step 2: Set Up Virtual Environment

In Bash console:
```bash
cd ~/your-repo
python3.10 -m venv venv  # PythonAnywhere free tier uses 3.10
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Django Settings

Edit your settings file:
```bash
nano mycricket/mycricket/settings.py
```

Update:
- `DEBUG = False`
- `ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']`
- Update `STATIC_ROOT` and `MEDIA_ROOT` paths

### Step 4: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### Step 5: Run Migrations

```bash
python manage.py migrate
```

### Step 6: Create Superuser

```bash
python manage.py createsuperuser
```

### Step 7: Create Media Directory

```bash
mkdir -p media/players
```

### Step 8: Configure Web App

1. Go to **Web** tab in PythonAnywhere Dashboard
2. Click **Add a new web app**
3. Choose **Manual configuration** → **Python 3.10**
4. Edit the WSGI file:

Replace the content with:
```python
import os
import sys

# Add your project directory to the path
path = '/home/yourusername/your-repo'
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'mycricket.mycricket.settings'

# Import Django's WSGI handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Step 9: Configure Static Files Mapping

In Web tab → **Static files** section:
- **URL**: `/static/`
- **Directory**: `/home/yourusername/your-repo/static`

- **URL**: `/media/`
- **Directory**: `/home/yourusername/your-repo/media`

### Step 10: Reload Web App

Click the green **Reload** button in the Web tab.

### Step 11: Access Your Site

Visit: `http://yourusername.pythonanywhere.com`

## Post-Deployment

### Setting Up Scheduled Tasks (Optional)

If you want to periodically fetch match data:
1. Go to **Tasks** tab
2. Create a scheduled task (requires paid account)

### Database Backup

Regularly backup your database:
```bash
python manage.py dumpdata > backup.json
```

## Troubleshooting

### Error: Module not found
- Ensure virtual environment is activated
- Check Python version matches (3.10 for free tier)

### Static files not loading
- Run `collectstatic` again
- Check Static files mapping in Web tab
- Ensure STATIC_ROOT path is correct

### 500 Error
- Check Error log in Web tab
- Ensure DEBUG=True temporarily to see errors
- Check file permissions

### Database errors
- Ensure migrations are run
- Check database file permissions

## Alternative: Deploy to Render.com (Free Tier)

Render.com also offers free Django hosting:

### Steps for Render:

1. **Sign up at Render.com**

2. **Connect your GitHub repository**

3. **Create a Web Service:**
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - Start Command: `gunicorn mycricket.mycricket.wsgi:application`

4. **Add Environment Variables:**
   - `DEBUG=False`
   - `SECRET_KEY=your-secret-key`
   - `ALLOWED_HOSTS=your-app.onrender.com`

5. **Use PostgreSQL (free tier):**
   - Add PostgreSQL database
   - Update DATABASES in settings.py

6. **Deploy!**

## Notes

- PythonAnywhere free tier: Limited to 1 web app, 512MB disk space
- Render.com free tier: Sleeps after inactivity, but good for testing
- For production, consider paid hosting (PythonAnywhere $5/month, Render $7/month)
- Always keep DEBUG=False in production
- Set strong SECRET_KEY
- Use environment variables for sensitive data

## Security Checklist

- [ ] DEBUG = False
- [ ] Strong SECRET_KEY
- [ ] ALLOWED_HOSTS configured
- [ ] Static files collected
- [ ] Media files directory created
- [ ] Database migrations applied
- [ ] Superuser created
- [ ] HTTPS enabled (on paid tiers)

