# Cricket API Integration Guide

This guide explains how to integrate real cricket API data with CricketDuel.

## Current Status

The application currently uses mock data for demonstration. To use real cricket match data, you need to:

1. Choose a cricket API provider
2. Get an API key
3. Configure the API in `core/services.py`
4. Run the sync command regularly

## Supported APIs

### Option 1: CricAPI (cricapi.com)
- Free tier available
- Provides live scores, matches, and player stats
- Sign up at: https://www.cricapi.com/

### Option 2: RapidAPI Cricket APIs
- Multiple cricket API providers
- Browse at: https://rapidapi.com/category/Sports
- Popular: Cricket Live Scores, Cricket API, etc.

### Option 3: SportsDataIO
- Paid service with comprehensive cricket data
- https://sportsdata.io/

## Configuration Steps

### Step 1: Get API Key

Sign up with your chosen provider and get an API key.

### Step 2: Update Settings

In `mycricket/settings.py`, add:

```python
# Cricket API Configuration
CRICKET_API_KEY = 'your_api_key_here'
CRICKET_API_URL = 'https://api.cricapi.com/v1'  # Or your API base URL
```

### Step 3: Update Service Layer

Update `core/services.py` to implement real API calls:

```python
def get_live_matches(self):
    try:
        response = requests.get(
            f"{self.base_url}/matches",
            params={'apikey': self.api_key, 'offset': 0}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return self._format_api_matches(data.get('data', []))
    except Exception as e:
        logger.error(f"API error: {str(e)}")
    return []
```

### Step 4: Sync Matches

Run the sync command to fetch and update matches:

```bash
python manage.py sync_matches --api cricapi
```

### Step 5: Set Up Scheduled Sync (Optional)

For automatic updates, set up a cron job or scheduled task:

```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/project && python manage.py sync_matches
```

Or use Django's management command with Celery for more advanced scheduling.

## Sync Command Usage

```bash
# Sync using mock data (default)
python manage.py sync_matches

# Sync using specific API
python manage.py sync_matches --api cricapi

# Update existing matches
python manage.py sync_matches --update-existing
```

## Data Structure

The sync command expects API data in this format:

```python
{
    'id': 'unique_match_id',
    'name': 'India vs Australia - T20',
    'team_a': {'id': 'team_1_id', 'name': 'India'},
    'team_b': {'id': 'team_2_id', 'name': 'Australia'},
    'status': 'live',  # or 'upcoming', 'completed'
    'date': '2025-12-23T10:00:00Z',
    'venue': 'Wankhede Stadium, Mumbai'
}
```

## Player Data

Player data can be synced from match squad endpoints. The sync command automatically fetches player lists for each match.

## Notes

- Always check API rate limits
- Cache API responses when possible
- Handle API errors gracefully
- Update match status regularly (live → completed)
- Consider using webhooks if API supports them






