# GitHub Actions Auto-Deployment Setup

This repository is configured to automatically deploy to PythonAnywhere whenever code is pushed to the `main` branch.

## Setup Instructions

### 1. Generate SSH Key for PythonAnywhere

On your local machine, generate an SSH key pair (if you don't have one):

```bash
ssh-keygen -t ed25519 -C "github-actions-pythonanywhere" -f ~/.ssh/pythonanywhere_deploy
```

### 2. Add Public Key to PythonAnywhere

Copy the public key:
```bash
cat ~/.ssh/pythonanywhere_deploy.pub
```

Add it to your PythonAnywhere account:
1. Go to PythonAnywhere Dashboard
2. Click on "Account" → "SSH keys"
3. Paste the public key and save

Or if using the console, add to `~/.ssh/authorized_keys`:
```bash
cat ~/.ssh/pythonanywhere_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3. Get PythonAnywhere API Token

1. Go to PythonAnywhere Dashboard
2. Click on "Account" → "API token"
3. Copy your API token (or create a new one)

### 4. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `PYTHONANYWHERE_HOST` | `ssh.pythonanywhere.com` | PythonAnywhere SSH host |
| `PYTHONANYWHERE_USERNAME` | Your PythonAnywhere username | Your PA username |
| `PYTHONANYWHERE_SSH_KEY` | Contents of `~/.ssh/pythonanywhere_deploy` (private key) | Private SSH key for authentication |
| `PYTHONANYWHERE_PROJECT_PATH` | `/home/yourusername/mysite` | Full path to your project directory on PA |
| `PYTHONANYWHERE_WEBAPP_DOMAIN` | `yourusername.pythonanywhere.com` | Your web app domain (without https://) |
| `PYTHONANYWHERE_API_TOKEN` | Your API token from step 3 | PA API token for reloading web app |

### 5. Set Up Git Repository on PythonAnywhere

SSH into PythonAnywhere and set up the git repository:

```bash
ssh yourusername@ssh.pythonanywhere.com
cd /home/yourusername/mysite  # or your project path
git clone https://github.com/shankar-mahato/cricket_society.git .
# Or if already cloned:
git remote add origin https://github.com/shankar-mahato/cricket_society.git
git pull origin main
```

### 6. Configure Git Credentials on PythonAnywhere (if needed)

If your repository is private, you may need to set up authentication:

```bash
# Option 1: Use SSH URL instead
git remote set-url origin git@github.com:shankar-mahato/cricket_society.git

# Option 2: Use Personal Access Token with HTTPS
git remote set-url origin https://YOUR_TOKEN@github.com/shankar-mahato/cricket_society.git
```

### 7. Configure WSGI File on PythonAnywhere

**CRITICAL STEP:** The WSGI file must be configured correctly for your project structure.

1. Go to PythonAnywhere Dashboard → Web tab
2. Click on your web app
3. Click on "WSGI configuration file" link
4. Replace the entire content with the configuration from `wsgi_pythonanywhere.py` in this repository
5. **Update the paths** in the WSGI file to match your actual PythonAnywhere paths:
   - `project_home = '/home/cricketsociety/cricket_society'` → Your actual project root
   - `mycricket_path = '/home/cricketsociety/cricket_society/mycricket'` → Your actual Django project path
6. Save and reload the web app

See `PYTHONANYWHERE_WSGI_CONFIG.md` for detailed instructions and troubleshooting.

### 8. Initial Setup on PythonAnywhere

Run these commands on PythonAnywhere for the first time:

```bash
cd /home/yourusername/mysite/mycricket  # Adjust path as needed
source ../venv/bin/activate  # Adjust venv path
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

### 8. Test the Deployment

1. Make a small change to your code
2. Commit and push to main branch:
   ```bash
   git add .
   git commit -m "Test auto-deployment"
   git push origin main
   ```
3. Check GitHub Actions tab to see the deployment progress
4. Verify the changes are live on your PythonAnywhere site

## Troubleshooting

### SSH Connection Issues

If deployment fails with SSH errors:
- Verify SSH key is correctly added to GitHub Secrets
- Check that the public key is in `~/.ssh/authorized_keys` on PythonAnywhere
- Test SSH connection manually: `ssh yourusername@ssh.pythonanywhere.com -i ~/.ssh/pythonanywhere_deploy`

### Git Pull Issues

If git pull fails:
- Ensure git is initialized in the project directory
- Check that remote URL is correct
- Verify credentials if using private repository

### API Token Issues

If web app reload fails:
- Verify API token is correct in GitHub Secrets
- Check that web app domain matches exactly (without https://)
- Test API token manually:
  ```bash
  curl -X POST https://www.pythonanywhere.com/api/v0/user/YOUR_USERNAME/webapps/YOUR_DOMAIN/reload/ \
    -H "Authorization: Token YOUR_TOKEN"
  ```

### Path Issues

- Ensure `PYTHONANYWHERE_PROJECT_PATH` points to the directory containing `manage.py`
- Adjust paths in the workflow file if your project structure differs

## Workflow Customization

You can customize the deployment workflow in `.github/workflows/deploy.yml`:

- Add pre-deployment steps (tests, linting, etc.)
- Add notifications (Slack, email, etc.)
- Add rollback mechanisms
- Customize deployment commands

## Security Notes

- Never commit SSH keys or API tokens to the repository
- Use GitHub Secrets for all sensitive information
- Rotate SSH keys and API tokens periodically
- Review GitHub Actions logs for any exposed secrets

