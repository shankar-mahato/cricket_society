# Populate Test Data

This guide explains how to populate the database with test data for testing the CricketDuel application.

## Usage

### Basic Usage (Adds data without clearing existing)

```bash
cd mycricket
python manage.py populate_test_data
```

### Clear existing data and populate fresh

```bash
python manage.py populate_test_data --clear
```

## What Gets Created

The script creates the following test data:

### 1. Teams (6 teams)
- India (IND)
- Australia (AUS)
- England (ENG)
- South Africa (SA)
- New Zealand (NZ)
- Pakistan (PAK)

### 2. Players (44 players total)
- **India**: 11 players including Virat Kohli, Rohit Sharma, KL Rahul, etc.
- **Australia**: 11 players including David Warner, Steve Smith, Glenn Maxwell, etc.
- **England**: 11 players including Jos Buttler, Ben Stokes, Joe Root, etc.
- **South Africa**: 11 players including Quinton de Kock, Kagiso Rabada, etc.

Each player includes:
- Name
- Role (Batsman, Bowler, All-rounder, Wicketkeeper)
- Batting Average
- Strike Rate

### 3. Matches (8 matches total)
- **Upcoming**: 4 matches (scheduled for future)
- **Live**: 2 matches (currently in progress)
- **Completed**: 2 matches (finished, with player statistics)

Matches include:
- Different teams competing
- Realistic venues and match titles
- Proper date/time settings

### 4. Player Match Statistics
- **For completed matches**: Player runs scored, balls faced, wickets
- Statistics added automatically for players in completed matches
- Helps test the betting settlement feature

### 5. Test Users (5 users)
- `player1` / `testpass123` (has ₹1000 wallet balance)
- `player2` / `testpass123`
- `player3` / `testpass123`
- `betuser1` / `testpass123` (has ₹1000 wallet balance)
- `betuser2` / `testpass123`

All users automatically have wallets created.

## Syncing Live Match Data

To sync real match data from cricket APIs (instead of test data):

```bash
python manage.py sync_matches
```

This will fetch live matches from the configured API and update the database. See `core/management/commands/README_API_SYNC.md` for API integration details.

## Example Workflow

1. **Run migrations** (if not already done):
   ```bash
   python manage.py migrate
   ```

2. **Option A: Populate test data** (for testing):
   ```bash
   python manage.py populate_test_data
   ```

   **Option B: Sync real match data** (for production):
   ```bash
   python manage.py sync_matches
   ```

3. **Login and test**:
   - Go to http://localhost:8000/accounts/login/
   - Login with `player1` / `testpass123`
   - Create a betting session on a match
   - Login with `player2` / `testpass123` in another browser/incognito
   - Join the session and start betting!

## Notes

- The `--clear` flag will delete existing data before populating (use with caution!)
- Player images need to be uploaded manually through admin if you want pictures
- Matches are set with realistic dates (some in past, some in future)
- Wallet balances are set to ₹1000 for player1 and betuser1 for testing

## Troubleshooting

If you get errors:
- Make sure migrations are run: `python manage.py migrate`
- If Pillow error appears (for player images), install it: `pip install Pillow`
- Check that all apps are in INSTALLED_APPS in settings.py

