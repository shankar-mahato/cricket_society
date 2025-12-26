# 🔧 Fixing 500 Error in deploy.py

## The Problem
You're getting a 500 error, which usually means:
1. The web app name is incorrect
2. The web app doesn't exist yet on PythonAnywhere
3. The API token might have issues

## Solution

### Step 1: Install requests in your virtual environment
```bash
# Make sure you're in the project root
cd /Users/shankar.mahato/DemoCricketAPP

# Activate your virtual environment (you're already in it based on your prompt)
# Then install requests
pip install requests
```

### Step 2: Find your correct web app name
1. Go to: https://www.pythonanywhere.com/user/cricketsociety/webapps/
2. Look at the list of web apps
3. Note the **exact name** of your web app (it might be different from 'cricketsociety')

### Step 3: Update deploy.py
Edit `deploy.py` and update `WEBAPP_NAME` to match the exact name from Step 2:

```python
WEBAPP_NAME = 'your_actual_webapp_name'  # Update this!
```

### Step 4: Run deploy.py again
```bash
python deploy.py
```

The improved script will now:
- Check if the web app exists
- Show you available web apps if there's an error
- Give you better error messages

---

## Alternative: Manual Reload

If the API method doesn't work, you can manually reload:

1. **SSH into PythonAnywhere:**
   - Go to: https://www.pythonanywhere.com/user/cricketsociety/consoles/
   - Open a Bash console

2. **Pull latest code:**
   ```bash
   cd ~/cricket_society
   git pull origin main
   ```

3. **Reload web app:**
   - Go to: https://www.pythonanywhere.com/user/cricketsociety/webapps/
   - Click the **Reload** button for your web app

---

## Common Issues

### Issue: "Web app not found"
- **Solution:** Check the exact web app name in PythonAnywhere dashboard
- Update `WEBAPP_NAME` in deploy.py

### Issue: "Invalid API token"
- **Solution:** Get a new token from: https://www.pythonanywhere.com/user/cricketsociety/api_token/
- Update `API_TOKEN` in deploy.py

### Issue: "User not found"
- **Solution:** Check your PythonAnywhere username
- Update `USERNAME` in deploy.py

---

## Quick Test

After updating, run:
```bash
python deploy.py
```

You should see:
```
🚀 Deploying to PythonAnywhere...
🔍 Checking web apps for user: cricketsociety...
   Found web apps: cricketsociety, another_app
🔄 Reloading web app: cricketsociety...
✅ Web app reloaded successfully!
   Visit: https://cricketsociety.pythonanywhere.com
```

