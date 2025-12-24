#!/bin/bash
# Quick deployment script for PythonAnywhere
# Run this after uploading your code to PythonAnywhere

echo "Setting up CricketDuel on PythonAnywhere..."

# Activate virtual environment (adjust path as needed)
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create media directories
mkdir -p media/players

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser (interactive)
echo "Creating superuser..."
python manage.py createsuperuser

echo "Setup complete! Don't forget to:"
echo "1. Update settings.py with your PythonAnywhere domain"
echo "2. Configure WSGI file in Web tab"
echo "3. Set up static/media file mappings"
echo "4. Reload your web app"




