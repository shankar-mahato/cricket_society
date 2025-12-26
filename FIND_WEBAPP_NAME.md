# 🔍 How to Find Your Web App Name on PythonAnywhere

## Method 1: Web Tab (Easiest)

1. **Log in to PythonAnywhere:**
   - Go to: https://www.pythonanywhere.com/
   - Log in with your account

2. **Go to Web Tab:**
   - Click on **"Web"** in the top navigation menu
   - Or go directly to: https://www.pythonanywhere.com/user/cricketsociety/webapps/

3. **Find Your Web App:**
   - You'll see a list of your web apps
   - The **name** is shown in the web app card/row
   - It might be:
     - `cricketsociety` (same as username)
     - `cricket_society` (with underscore)
     - Or any custom name you gave it

4. **Check the URL:**
   - Look at the web app's URL in the dashboard
   - It will show: `https://cricketsociety.pythonanywhere.com/`
   - The web app name is usually the part before `.pythonanywhere.com`

## Method 2: Using the API (Programmatic)

You can also check using the deploy script itself. The script will show you all available web apps when you run it.

## Method 3: Check Web App Settings

1. Go to **Web** tab
2. Click on your web app (if you have one)
3. Look at the **"Configuration"** section
4. The web app name is usually shown at the top

## Common Web App Names

- If username is `cricketsociety`, web app name is usually:
  - `cricketsociety` (most common)
  - `cricket_society` (if created with underscore)
  - Or a custom name you chose

## If You Don't Have a Web App Yet

If you don't see any web apps, you need to create one first:

1. Go to **Web** tab
2. Click **"Add a new web app"**
3. Choose **"Manual configuration"**
4. Select **Python 3.10** (or latest available)
5. Click **Next** until created
6. The web app will be created with a default name (usually your username)

## Quick Check

Run this in your terminal to see what the script finds:

```bash
python deploy.py
```

The script will show:
```
🔍 Checking web apps for user: cricketsociety...
   Found web apps: cricket_society, another_app
```

This tells you exactly what web apps you have!

