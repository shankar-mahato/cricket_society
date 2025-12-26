# 🔧 Fix: UI Not Reflecting on PythonAnywhere

## Problem
UI changes aren't showing on PythonAnywhere even after deploying.

## Root Cause
The `deploy.py` script only reloads the web app but doesn't:
1. Pull the latest code from GitHub
2. Collect static files (CSS/JS/images)
3. Run database migrations

## Solution

### Option 1: Quick Fix (Recommended)

**On PythonAnywhere**, run these commands:

```bash
cd ~/cricket_society
git pull origin main
source venv/bin/activate
cd mycricket
python manage.py collectstatic --noinput
python manage.py migrate  # if needed
```

Then reload the web app:
- Go to **Web** tab → Click **Reload** button
- OR run: `python deploy.py` from your local machine

### Option 2: Use Deployment Script

1. **Upload the deployment script to PythonAnywhere:**
   - Copy `deploy_on_pythonanywhere.sh` to PythonAnywhere
   - Or create it directly on PythonAnywhere

2. **Make it executable:**
   ```bash
   chmod +x deploy_on_pythonanywhere.sh
   ```

3. **Run it:**
   ```bash
   bash deploy_on_pythonanywhere.sh
   ```

This script will automatically:
- ✅ Pull latest code from GitHub
- ✅ Update dependencies
- ✅ Run migrations
- ✅ Collect static files (IMPORTANT for UI!)
- ✅ Reload the web app

### Option 3: Manual Steps

1. **Push code to GitHub** (if not done):
   ```bash
   git add .
   git commit -m "Update UI"
   git push origin main
   ```

2. **SSH into PythonAnywhere** and run:
   ```bash
   cd ~/cricket_society
   git pull origin main
   source venv/bin/activate
   cd mycricket
   python manage.py collectstatic --noinput
   python manage.py migrate
   ```

3. **Reload web app:**
   - Go to PythonAnywhere Dashboard → **Web** tab
   - Click **Reload** button

4. **Clear browser cache:**
   - Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
   - Or clear browser cache completely

## Why This Happens

Django's static files (CSS, JavaScript, images) need to be collected into the `staticfiles` directory after code changes. The `collectstatic` command:
- Gathers all static files from your apps
- Copies them to `STATIC_ROOT` (usually `staticfiles/`)
- Makes them available to be served by the web server

**Without running `collectstatic`, your new CSS/JS files won't be available on the server!**

## Verification

After deployment, check:

1. **Static files are collected:**
   ```bash
   ls -la ~/cricket_society/mycricket/staticfiles/
   ```
   Should show CSS, JS, and other static files.

2. **Static files mapping is correct:**
   - Go to **Web** tab → **Static files** section
   - Should have: `/static/` → `/home/cricketsociety/cricket_society/mycricket/staticfiles/`

3. **Browser cache:**
   - Open site in incognito/private window
   - Or hard refresh (Ctrl+Shift+R)

## Prevention

To avoid this in the future:

1. **Always run `collectstatic` after code changes:**
   ```bash
   python manage.py collectstatic --noinput
   ```

2. **Use the deployment script** (`deploy_on_pythonanywhere.sh`) which does everything automatically

3. **Set up a scheduled task** (if you have paid account) to auto-deploy on git push

## Quick Checklist

- [ ] Code pushed to GitHub
- [ ] Code pulled on PythonAnywhere (`git pull`)
- [ ] Static files collected (`collectstatic`)
- [ ] Migrations run (if needed)
- [ ] Web app reloaded
- [ ] Browser cache cleared

## Still Not Working?

1. **Check PythonAnywhere error logs:**
   - Go to **Web** tab → **Error log**
   - Look for static file errors

2. **Verify static files directory:**
   ```bash
   ls -la ~/cricket_society/mycricket/staticfiles/
   ```

3. **Check static files URL mapping:**
   - Web tab → Static files section
   - URL: `/static/`
   - Directory: `/home/cricketsociety/cricket_society/mycricket/staticfiles/`

4. **Test static file directly:**
   - Visit: `https://cricketsociety.pythonanywhere.com/static/admin/css/base.css`
   - Should load the CSS file (not 404)

5. **Check browser console:**
   - Open DevTools (F12)
   - Look for 404 errors on CSS/JS files

