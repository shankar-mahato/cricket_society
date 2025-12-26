#!/usr/bin/env python3
"""
Automatic deployment script for PythonAnywhere
Run this after pushing to GitHub to reload your web app

Usage:
    python deploy.py
    OR
    cd /Users/shankar.mahato/DemoCricketAPP && python deploy.py
"""
import sys
import os

# Try to import requests, if not available, provide helpful error
try:
    import requests
except ImportError:
    print('❌ Error: requests module not found')
    print('   Install it with: pip install requests')
    print('   Or activate your virtual environment first')
    sys.exit(1)

# Configuration
username = 'cricketsociety'
token = 'dec6d26a6576c80ce27cfda4160413d88e57f787'
webapp_name = 'cricketsociety'  # Just the web app name (not the full domain). Update after creating web app.

def get_webapps():
    """Get list of web apps for the user"""
    url = 'https://www.pythonanywhere.com/api/v0/user/{username}/webapps/'.format(
        username=username
    )
    headers = {'Authorization': 'Token {token}'.format(token=token)}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print('❌ Error getting web apps: status code {}'.format(response.status_code))
            print('   Response: {!r}'.format(response.content))
            return None
    except requests.exceptions.RequestException as e:
        print('❌ Error connecting to PythonAnywhere: {}'.format(e))
        return None

def reload_webapp():
    """Reload PythonAnywhere web app via API"""
    if not token or len(token) < 20:
        print('❌ Error: Invalid API token')
        print('   Get your API token from: https://www.pythonanywhere.com/user/{}/api_token/'.format(username))
        return False
    
    # First, check available web apps
    print('🔍 Checking web apps for user: {}...'.format(username))
    webapps = get_webapps()
    
    if webapps is None:
        return False
    
    if not webapps:
        print('❌ No web apps found for user: {}'.format(username))
        print('\n📝 You need to create a web app first!')
        print('   Steps:')
        print('   1. Go to: https://www.pythonanywhere.com/user/{}/webapps/'.format(username))
        print('   2. Click "Add a new web app"')
        print('   3. Choose "Manual configuration"')
        print('   4. Select Python 3.10 (or latest)')
        print('   5. Complete the setup')
        print('   6. Note the web app name it creates')
        print('   7. Update webapp_name in deploy.py')
        return False
    
    # Extract web app names - handle different response formats
    webapp_names = []
    for app in webapps:
        # API might return dict with 'name' key or just a string
        if isinstance(app, dict):
            name = app.get('name', '') or app.get('domain_name', '').replace('.pythonanywhere.com', '')
            if name:
                webapp_names.append(name)
        elif isinstance(app, str):
            # Remove domain part if present
            clean_name = app.replace('.pythonanywhere.com', '')
            webapp_names.append(clean_name)
    
    print('   Found web apps: {}'.format(', '.join(webapp_names) if webapp_names else 'None'))
    
    # Also try domain name format (cricketsociety.pythonanywhere.com -> cricketsociety)
    webapp_name_clean = webapp_name.replace('.pythonanywhere.com', '').replace('.', '_')
    
    # Check if the specified web app exists (try both formats)
    if webapp_name not in webapp_names and webapp_name_clean not in webapp_names:
        print('\n❌ Error: Web app "{}" not found!'.format(webapp_name))
        print('   Available web apps: {}'.format(', '.join(webapp_names) if webapp_names else 'None'))
        if webapp_names:
            print('\n💡 Tip: Update webapp_name in deploy.py to one of: {}'.format(', '.join(webapp_names)))
            # Auto-suggest the first available web app
            if webapp_names:
                suggested_name = webapp_names[0]
                print('   Suggested: webapp_name = \'{}\''.format(suggested_name))
        else:
            print('   Please create a web app first (see instructions above)')
        return False
    
    # Use the correct name format
    actual_webapp_name = webapp_name if webapp_name in webapp_names else webapp_name_clean
    
    # Now try to reload
    print('🔄 Reloading web app: {}...'.format(actual_webapp_name))
    url = 'https://www.pythonanywhere.com/api/v0/user/{username}/webapps/{webapp_name}/reload/'.format(
        username=username,
        webapp_name=actual_webapp_name
    )
    headers = {'Authorization': 'Token {token}'.format(token=token)}
    
    try:
        response = requests.post(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print('✅ Web app reloaded successfully!')
            print('   Visit: https://{}.pythonanywhere.com'.format(username))
            return True
        elif response.status_code == 404:
            print('❌ Error: Web app "{}" not found'.format(actual_webapp_name))
            print('   Available web apps: {}'.format(', '.join(webapp_names)))
            print('   Tried name: {}'.format(actual_webapp_name))
            return False
        elif response.status_code == 401:
            print('❌ Error: Invalid API token')
            print('   Please check your API token at: https://www.pythonanywhere.com/user/{}/api_token/'.format(username))
            return False
        elif response.status_code == 500:
            print('❌ Error: PythonAnywhere server error (500)')
            print('   This usually means:')
            print('   1. The web app has an error and cannot be reloaded')
            print('   2. Check your PythonAnywhere dashboard for web app errors')
            print('   3. Try reloading manually from the dashboard first')
            return False
        else:
            print('❌ Error: status code {}'.format(response.status_code))
            print('   Response: {!r}'.format(response.content[:200]))
            return False
            
    except requests.exceptions.RequestException as e:
        print('❌ Error connecting to PythonAnywhere: {}'.format(e))
        return False

def print_deployment_instructions():
    """Print instructions for complete deployment"""
    print('\n' + '='*60)
    print('📋 COMPLETE DEPLOYMENT STEPS')
    print('='*60)
    print('\n⚠️  IMPORTANT: The deploy.py script only reloads the web app.')
    print('   You need to pull code and collect static files on PythonAnywhere!')
    print('\n📝 Steps to deploy latest UI changes:')
    print('\n1️⃣  Push your code to GitHub (if not already done):')
    print('   git add .')
    print('   git commit -m "Update UI"')
    print('   git push origin main')
    print('\n2️⃣  SSH into PythonAnywhere and run:')
    print('   cd ~/cricket_society')
    print('   git pull origin main')
    print('   source venv/bin/activate')
    print('   cd mycricket')
    print('   python manage.py collectstatic --noinput')
    print('   python manage.py migrate  # if needed')
    print('\n3️⃣  Then run this script to reload:')
    print('   python deploy.py')
    print('\n💡 TIP: You can also run the deployment script on PythonAnywhere:')
    print('   bash deploy_on_pythonanywhere.sh')
    print('='*60 + '\n')

if __name__ == '__main__':
    print('🚀 Deploying to PythonAnywhere...')
    print_deployment_instructions()
    success = reload_webapp()
    if success:
        print('\n✅ Web app reloaded!')
        print('⚠️  Remember: If UI changes aren\'t showing, make sure you:')
        print('   1. Pulled latest code on PythonAnywhere (git pull)')
        print('   2. Ran collectstatic (python manage.py collectstatic --noinput)')
        print('   3. Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)')
    sys.exit(0 if success else 1)
