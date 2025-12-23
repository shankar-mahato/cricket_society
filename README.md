# Cricket Betting App - Django

A Django-based cricket betting application where two players can create betting sessions, pick players from live matches, place bets, and win money based on player performance.

## Features

1. **Match Management**
   - View live and upcoming cricket matches
   - Match details with team and player information
   - Integration with cricket APIs (mock implementation included)

2. **Betting Sessions**
   - Two players can create/join betting sessions
   - Random turn selection for player picking
   - Configurable number of players per team side
   - Turn-based player selection

3. **Player Picking**
   - Players take turns picking players from both teams
   - Validation to ensure fair selection (each player picks equal number from each team)
   - Real-time session updates

4. **Betting System**
   - Place bets on picked players (amount per run)
   - Payout calculation: `runs_scored × amount_per_run`
   - Automatic wallet updates after match completion

5. **Wallet System**
   - User wallets with balance tracking
   - Deposit functionality
   - Transaction history
   - Automatic winnings credit after match settlement

## Installation

1. **Clone the repository and navigate to the project:**
   ```bash
   cd mycricket
   ```

2. **Activate virtual environment:**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies (if needed):**
   ```bash
   pip install django requests
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

7. **Access the application:**
   - Home: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## Usage

### For Users:

1. **Sign Up/Login**:
   - Click "Sign Up" to create a new account
   - Fill in username, email, and password
   - Wallet is automatically created for new users
   - Use "Login" to access your account
   - Use "Forgot Password" to reset your password via email

2. **View Matches**: Browse live and upcoming matches on the home page.

3. **Create Betting Session**:
   - Select a match
   - Choose number of players per side (1-11)
   - Create session and wait for another player to join

4. **Join Session**: View available sessions on match detail page and join one.

5. **Pick Players**:
   - Players take turns picking players
   - Each player must pick equal number from each team
   - System enforces turn order

6. **Place Bets**:
   - After all players are picked, place bets on your players
   - Enter amount per run for each player

7. **Settle Session**:
   - After match completion, click "Settle Session"
   - System fetches player runs from API
   - Winnings are automatically added to wallet

8. **Wallet Management**:
   - Deposit money to wallet
   - View transaction history
   - Check balance

### For Administrators:

- Access admin panel at `/admin/`
- Manage all models: Teams, Players, Matches, Sessions, Bets, Wallets, Transactions
- Create/manage match data
- View all betting activity

## API Integration

The application includes a `CricketAPIService` class in `core/services.py` that can be extended to integrate with real cricket APIs like:
- CricAPI
- SportsDataIO
- RapidAPI Cricket APIs

Currently, it uses mock data for demonstration. To integrate with a real API:

1. Get an API key from your preferred cricket API provider
2. Add to `settings.py`:
   ```python
   CRICKET_API_KEY = 'your_api_key_here'
   CRICKET_API_URL = 'https://api.example.com/v1'
   ```
3. Update the service methods in `core/services.py` to make actual API calls

## Models

- **Team**: Cricket teams
- **Player**: Players with team association
- **Match**: Cricket matches with teams and status
- **PlayerMatchStats**: Player statistics for specific matches
- **Wallet**: User wallet with balance
- **Transaction**: Wallet transaction history
- **BettingSession**: Betting session between two players
- **PickedPlayer**: Players picked by betters in a session
- **Bet**: Bet placed on a picked player with amount per run

## Workflow

1. User A creates a betting session for a match
2. User B joins the session
3. System randomly decides who picks first
4. Players take turns picking players (alternating turns)
5. Once all players are picked, betting phase begins
6. Each player places bets (amount per run) on their picked players
7. After match completion, admin/user clicks "Settle Session"
8. System fetches player runs from API
9. Winnings calculated: `runs × amount_per_run`
10. Winnings automatically added to respective wallets

## Future Enhancements

- Real-time updates using WebSockets
- Automatic match status updates via scheduled tasks (Celery)
- Advanced statistics and analytics
- Multi-match betting sessions
- Leaderboards and rankings
- Email notifications

## Authentication Features

The application includes a complete authentication system:

1. **User Signup**
   - Custom signup form with username, email, and password
   - Email validation (unique email required)
   - Password strength validation
   - Automatic wallet creation for new users
   - Auto-login after successful signup

2. **User Login**
   - Secure login with username and password
   - Session management
   - Remember user session

3. **Password Reset**
   - Forgot password functionality
   - Email-based password reset
   - Secure token-based reset links
   - Password reset confirmation

4. **Email Configuration**
   - Development: Emails printed to console (default)
   - Production: Configure SMTP settings in `settings.py`
   - To use email in production, update EMAIL_BACKEND and SMTP settings

## Notes

- This is a demonstration application
- Ensure compliance with local gambling/betting laws before deploying
- For production, configure proper email settings (SMTP) for password reset
- Implement proper security measures for financial transactions
- Use production-grade database (PostgreSQL) instead of SQLite
- Add comprehensive error handling and logging
- Implement rate limiting and API throttling
- Enable HTTPS in production for secure password transmission

## License

This project is for educational purposes.
# cricket_society
