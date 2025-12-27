"""
Service module for fetching cricket data from external APIs
Supports multiple free cricket APIs
"""
try:
    import requests
except ImportError:
    requests = None

from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CricketAPIService:
    """
    Service to fetch cricket data from free APIs.
    Currently supports CricAPI and can be extended for other APIs.
    """
    
    def __init__(self):
        # You can configure API key in settings.py
        # For demo purposes, we'll use a mock service
        self.api_key = getattr(settings, 'CRICKET_API_KEY', '29703eb7-9d28-44e5-a732-33527c70afbf')
        self.base_url = getattr(settings, 'CRICKET_API_URL', 'https://api.cricapi.com/v1')
    
    def get_live_matches(self):
        """
        Fetch live cricket matches from API
        Returns list of match dictionaries with structure:
        {
            'id': 'match_id',
            'name': 'Match Title',
            'team_a': {'id': 'team_id', 'name': 'Team Name'},
            'team_b': {'id': 'team_id', 'name': 'Team Name'},
            'status': 'live',
            'date': 'ISO datetime string',
            'venue': 'Venue Name'
        }
        """
        try:
            # Try to fetch from real API if configured
            if self.api_key and requests:
                try:
                    # Fetch current matches from CricAPI
                    response = requests.get(
                        f"{self.base_url}/currentMatches",
                        params={'apikey': self.api_key, 'offset': 0},
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') == 'success':
                            matches = data.get('data', [])
                            # Filter for live matches: matchStarted=true and matchEnded=false
                            live_matches = [
                                m for m in matches 
                                if m.get('matchStarted', False) and not m.get('matchEnded', False)
                            ]
                            formatted = self._format_api_matches(live_matches)
                            logger.info(f"Fetched {len(formatted)} live matches from CricAPI")
                            return formatted
                    else:
                        logger.warning(f"CricAPI returned status {response.status_code}: {response.text}")
                except Exception as api_error:
                    logger.warning(f"API call failed, using mock data: {str(api_error)}")
            
            # Fallback to mock data
            return self._get_mock_matches()
        except Exception as e:
            logger.error(f"Error fetching live matches: {str(e)}")
            return []
    
    def _format_api_matches(self, api_data):
        """Format API response data to standard format"""
        formatted = []
        for match in api_data:
            # Extract team names from teams array
            teams = match.get('teams', [])
            team_info = match.get('teamInfo', [])
            
            # Get team names
            team_a_name = teams[0] if len(teams) > 0 else 'Team A'
            team_b_name = teams[1] if len(teams) > 1 else 'Team B'
            
            # Try to get team IDs from teamInfo
            team_a_id = None
            team_b_id = None
            for info in team_info:
                if info.get('name') == team_a_name:
                    team_a_id = f"cricapi_team_{team_a_name.lower().replace(' ', '_').replace('-', '_')}"
                elif info.get('name') == team_b_name:
                    team_b_id = f"cricapi_team_{team_b_name.lower().replace(' ', '_').replace('-', '_')}"
            
            # Fallback to generated IDs if not found
            if not team_a_id:
                team_a_id = f"cricapi_team_{team_a_name.lower().replace(' ', '_').replace('-', '_')}"
            if not team_b_id:
                team_b_id = f"cricapi_team_{team_b_name.lower().replace(' ', '_').replace('-', '_')}"
            
            # Determine status
            if match.get('matchStarted', False) and not match.get('matchEnded', False):
                status = 'live'
            elif match.get('matchEnded', False):
                status = 'completed'
            else:
                status = 'upcoming'
            
            formatted.append({
                'id': match.get('id', ''),
                'name': match.get('name', f"{team_a_name} vs {team_b_name}"),
                'team_a': {
                    'id': team_a_id,
                    'name': team_a_name,
                    'short_name': next((info.get('shortname', '') for info in team_info if info.get('name') == team_a_name), team_a_name[:3].upper())
                },
                'team_b': {
                    'id': team_b_id,
                    'name': team_b_name,
                    'short_name': next((info.get('shortname', '') for info in team_info if info.get('name') == team_b_name), team_b_name[:3].upper())
                },
                'status': status,
                'date': match.get('dateTimeGMT', match.get('date', '')),
                'venue': match.get('venue', 'TBA')
            })
        return formatted
    
    def get_upcoming_matches(self):
        """Fetch upcoming cricket matches"""
        try:
            # Try to fetch from real API if configured
            if self.api_key and requests:
                try:
                    # Fetch current matches from CricAPI
                    response = requests.get(
                        f"{self.base_url}/currentMatches",
                        params={'apikey': self.api_key, 'offset': 0},
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') == 'success':
                            matches = data.get('data', [])
                            # Filter for upcoming matches: matchStarted=false
                            upcoming_matches = [
                                m for m in matches 
                                if not m.get('matchStarted', False)
                            ]
                            formatted = self._format_api_matches(upcoming_matches)
                            logger.info(f"Fetched {len(formatted)} upcoming matches from CricAPI")
                            return formatted
                    else:
                        logger.warning(f"CricAPI returned status {response.status_code}: {response.text}")
                except Exception as api_error:
                    logger.warning(f"API call failed, using mock data: {str(api_error)}")
            
            # Fallback to mock data
            return self._get_mock_upcoming_matches()
        except Exception as e:
            logger.error(f"Error fetching upcoming matches: {str(e)}")
            return []
    
    def get_match_details(self, match_id):
        """
        Fetch detailed information about a specific match
        """
        try:
            # Mock implementation
            return self._get_mock_match_details(match_id)
        except Exception as e:
            logger.error(f"Error fetching match details: {str(e)}")
            return None
    
    def get_match_squad(self, match_id):
        """
        Get squad/players for a match
        Returns dict with team_a_players and team_b_players
        """
        try:
            # Mock implementation
            return self._get_mock_squad(match_id)
        except Exception as e:
            logger.error(f"Error fetching match squad: {str(e)}")
            return {'team_a_players': [], 'team_b_players': []}
    
    def get_match_score(self, match_id):
        """
        Get current score and player stats for a match
        Returns dict with player runs, wickets, etc.
        """
        try:
            # Mock implementation
            return self._get_mock_match_score(match_id)
        except Exception as e:
            logger.error(f"Error fetching match score: {str(e)}")
            return {}
    
    def get_player_stats_in_match(self, match_id, player_id):
        """
        Get specific player's statistics in a match
        Returns dict with runs, balls, wickets, etc.
        """
        try:
            score_data = self.get_match_score(match_id)
            return score_data.get('player_stats', {}).get(str(player_id), {})
        except Exception as e:
            logger.error(f"Error fetching player stats: {str(e)}")
            return {}
    
    # Mock data methods for demonstration
    def _get_mock_matches(self):
        """Mock live matches data - tries to get from database first"""
        # Get real matches from database if available (synced data)
        try:
            from core.models import Match
            db_matches = Match.objects.filter(status='live')
            if db_matches.exists():
                matches = []
                for match in db_matches:
                    matches.append({
                        'id': match.api_id,
                        'name': match.match_title,
                        'team_a': {'id': match.team_a.api_id, 'name': match.team_a.name},
                        'team_b': {'id': match.team_b.api_id, 'name': match.team_b.name},
                        'status': match.status,
                        'date': match.match_date.isoformat(),
                        'venue': match.venue or 'TBA',
                    })
                return matches
        except Exception:
            pass
        
        # Fallback: return empty list if no database matches
        # This ensures the app only shows matches that have been synced
        return []
    
    def _get_mock_upcoming_matches(self):
        """Mock upcoming matches data - tries to get from database first"""
        # Get real matches from database if available (synced data)
        try:
            from core.models import Match
            db_matches = Match.objects.filter(status='upcoming')
            if db_matches.exists():
                matches = []
                for match in db_matches:
                    matches.append({
                        'id': match.api_id,
                        'name': match.match_title,
                        'team_a': {'id': match.team_a.api_id, 'name': match.team_a.name},
                        'team_b': {'id': match.team_b.api_id, 'name': match.team_b.name},
                        'status': match.status,
                        'date': match.match_date.isoformat(),
                        'venue': match.venue or 'TBA',
                    })
                return matches
        except Exception:
            pass
        
        # Fallback: return empty list if no database matches
        return []
    
    def _get_mock_match_details(self, match_id):
        """Mock match details"""
        return {
            'id': match_id,
            'name': 'India vs Australia - T20 Series',
            'team_a': {'id': 'team_ind', 'name': 'India'},
            'team_b': {'id': 'team_aus', 'name': 'Australia'},
            'status': 'live',
            'venue': 'Wankhede Stadium, Mumbai',
            'date': timezone.now().isoformat(),
        }
    
    def _get_mock_squad(self, match_id):
        """Mock squad data"""
        return {
            'team_a_players': [
                {'id': 'player_1', 'name': 'Virat Kohli', 'role': 'Batsman'},
                {'id': 'player_2', 'name': 'Rohit Sharma', 'role': 'Batsman'},
                {'id': 'player_3', 'name': 'KL Rahul', 'role': 'Batsman'},
                {'id': 'player_4', 'name': 'Rishabh Pant', 'role': 'Wicketkeeper'},
                {'id': 'player_5', 'name': 'Hardik Pandya', 'role': 'All-rounder'},
                {'id': 'player_6', 'name': 'Ravindra Jadeja', 'role': 'All-rounder'},
                {'id': 'player_7', 'name': 'Jasprit Bumrah', 'role': 'Bowler'},
            ],
            'team_b_players': [
                {'id': 'player_8', 'name': 'David Warner', 'role': 'Batsman'},
                {'id': 'player_9', 'name': 'Steve Smith', 'role': 'Batsman'},
                {'id': 'player_10', 'name': 'Glenn Maxwell', 'role': 'All-rounder'},
                {'id': 'player_11', 'name': 'Alex Carey', 'role': 'Wicketkeeper'},
                {'id': 'player_12', 'name': 'Pat Cummins', 'role': 'Bowler'},
                {'id': 'player_13', 'name': 'Mitchell Starc', 'role': 'Bowler'},
                {'id': 'player_14', 'name': 'Josh Hazlewood', 'role': 'Bowler'},
            ]
        }
    
    def _get_mock_match_score(self, match_id):
        """Mock match score with player stats"""
        return {
            'player_stats': {
                'player_1': {'runs': 45, 'balls': 32, 'wickets': 0},
                'player_2': {'runs': 38, 'balls': 28, 'wickets': 0},
                'player_3': {'runs': 25, 'balls': 20, 'wickets': 0},
                'player_8': {'runs': 52, 'balls': 35, 'wickets': 0},
                'player_9': {'runs': 30, 'balls': 25, 'wickets': 0},
            }
        }


# Real API implementation example (uncomment when you have API key):
"""
class CricAPIService(CricketAPIService):
    def get_live_matches(self):
        try:
            response = requests.get(
                f"{self.base_url}/matches",
                params={'apikey': self.api_key, 'offset': 0}
            )
            data = response.json()
            if data.get('status') == 'success':
                return data.get('data', [])
            return []
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return []
"""


class OddsAPIService:
    """
    Service to fetch cricket data from The Odds API (the-odds-api.com)
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'ODDS_API_KEY', None)
        self.base_url = getattr(settings, 'ODDS_API_BASE_URL', 'https://api.the-odds-api.com/v4')
        self.cricket_sport_keys = [
            'cricket_test_match',
            'cricket_odi',
            'cricket_t20',
            'cricket_big_bash',
            'cricket_ipl',
            'cricket_psl',
            'cricket_cpl',
            'cricket_bb',
            'cricket_world_cup',
        ]
    
    def get_cricket_sports(self):
        """
        Get list of available cricket sports from The Odds API
        Returns list of sport objects
        """
        if not self.api_key or not requests:
            logger.warning("Odds API key not configured or requests library not available")
            return []
        
        try:
            url = f"{self.base_url}/sports"
            response = requests.get(url, params={'apiKey': self.api_key}, timeout=10)
            
            if response.status_code == 200:
                sports = response.json()
                # Filter for cricket sports
                cricket_sports = [sport for sport in sports if 'cricket' in sport.get('key', '').lower()]
                logger.info(f"Found {len(cricket_sports)} cricket sports")
                return cricket_sports
            else:
                logger.error(f"Odds API error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error fetching cricket sports from Odds API: {str(e)}")
            return []
    
    def get_upcoming_matches_24h(self):
        """
        Get upcoming cricket matches in the next 24 hours from The Odds API
        Returns list of match dictionaries with structure:
        {
            'id': 'event_id',
            'name': 'Match Title',
            'team_a': {'id': 'team_id', 'name': 'Team Name'},
            'team_b': {'id': 'team_id', 'name': 'Team Name'},
            'status': 'upcoming',
            'date': 'ISO datetime string',
            'venue': 'Venue Name' (if available)
        }
        """
        if not self.api_key or not requests:
            logger.warning("Odds API key not configured or requests library not available")
            return []
        
        all_matches = []
        now = timezone.now()
        next_24h = now + timedelta(hours=24)
        
        # Try to get cricket sports first
        cricket_sports = self.get_cricket_sports()
        if not cricket_sports:
            # Fallback to known cricket sport keys
            cricket_sports = [{'key': key} for key in self.cricket_sport_keys]
        
        for sport in cricket_sports:
            sport_key = sport.get('key')
            if not sport_key:
                continue
            
            try:
                url = f"{self.base_url}/sports/{sport_key}/odds"
                params = {
                    'apiKey': self.api_key,
                    'regions': 'us,uk,au',  # Multiple regions for better coverage
                    'markets': 'h2h',  # Head to head market
                    'oddsFormat': 'decimal',
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    matches = response.json()
                    
                    for match in matches:
                        try:
                            # Parse commence_time
                            commence_time_str = match.get('commence_time', '')
                            if commence_time_str:
                                commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                                if timezone.is_naive(commence_time):
                                    commence_time = timezone.make_aware(commence_time)
                                
                                # Filter for matches in next 24 hours
                                if now <= commence_time <= next_24h:
                                    home_team = match.get('home_team', '')
                                    away_team = match.get('away_team', '')
                                    
                                    # Determine which team is team_a and team_b
                                    # Use home_team as team_a and away_team as team_b
                                    # Generate unique team IDs
                                    team_a_id = f"odds_team_{home_team.lower().replace(' ', '_').replace('-', '_')}"
                                    team_b_id = f"odds_team_{away_team.lower().replace(' ', '_').replace('-', '_')}"
                                    
                                    formatted_match = {
                                        'id': match.get('id', ''),
                                        'name': f"{home_team} vs {away_team}",
                                        'team_a': {
                                            'id': team_a_id,
                                            'name': home_team
                                        },
                                        'team_b': {
                                            'id': team_b_id,
                                            'name': away_team
                                        },
                                        'status': 'upcoming',
                                        'date': commence_time.isoformat(),
                                        'venue': match.get('sport_title', 'TBA'),  # Use sport title as venue fallback
                                        'sport_key': sport_key,
                                    }
                                    all_matches.append(formatted_match)
                        except Exception as e:
                            logger.warning(f"Error parsing match {match.get('id', 'unknown')}: {str(e)}")
                            continue
                
                elif response.status_code == 429:
                    logger.warning("Rate limit reached for Odds API")
                    break
                else:
                    logger.warning(f"Odds API error for sport {sport_key}: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error fetching matches for sport {sport_key}: {str(e)}")
                continue
        
        # Remove duplicates based on match ID
        seen_ids = set()
        unique_matches = []
        for match in all_matches:
            if match['id'] not in seen_ids:
                seen_ids.add(match['id'])
                unique_matches.append(match)
        
        logger.info(f"Found {len(unique_matches)} upcoming matches in next 24 hours")
        return unique_matches
    
    def get_match_participants(self, event_id, sport_key='cricket_t20'):
        """
        Get participants/players for a specific match from The Odds API
        Returns dict with team_a_players and team_b_players
        """
        if not self.api_key or not requests:
            logger.warning("Odds API key not configured or requests library not available")
            return {'team_a_players': [], 'team_b_players': []}
        
        try:
            url = f"{self.base_url}/sports/{sport_key}/events/{event_id}/participants"
            response = requests.get(url, params={'apiKey': self.api_key}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                participants = data.get('participants', [])
                
                # The Odds API returns participants, but we need to map them to teams
                # Since we don't know which team they belong to from the API,
                # we'll return all participants and let the sync logic handle team assignment
                team_a_players = []
                team_b_players = []
                
                # Split participants - typically first half for team_a, second half for team_b
                # This is a heuristic and may need adjustment based on actual API response
                mid_point = len(participants) // 2
                
                for i, participant in enumerate(participants):
                    player_name = participant.get('name', '')
                    if player_name:
                        player_data = {
                            'id': f"player_{participant.get('id', i)}",
                            'name': player_name,
                            'role': 'Player',  # The Odds API doesn't provide role info
                        }
                        
                        if i < mid_point:
                            team_a_players.append(player_data)
                        else:
                            team_b_players.append(player_data)
                
                return {
                    'team_a_players': team_a_players,
                    'team_b_players': team_b_players
                }
            else:
                logger.warning(f"Could not fetch participants for event {event_id}: {response.status_code}")
                return {'team_a_players': [], 'team_b_players': []}
                
        except Exception as e:
            logger.error(f"Error fetching participants for event {event_id}: {str(e)}")
            return {'team_a_players': [], 'team_b_players': []}
    
    def get_match_players_alternative(self, event_id, sport_key, home_team, away_team):
        """
        Alternative method to get players by trying to fetch from event odds
        This is a workaround since The Odds API may not always have participants endpoint
        Returns dict with team_a_players and team_b_players
        """
        if not self.api_key or not requests:
            return {'team_a_players': [], 'team_b_players': []}
        
        try:
            # Try to get player markets from odds endpoint
            url = f"{self.base_url}/sports/{sport_key}/events/{event_id}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us,uk,au',
                'markets': 'player_runs,player_wickets',  # Player-specific markets
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                bookmakers = data.get('bookmakers', [])
                
                # Extract player names from markets
                players_set = set()
                
                for bookmaker in bookmakers:
                    markets = bookmaker.get('markets', [])
                    for market in markets:
                        outcomes = market.get('outcomes', [])
                        for outcome in outcomes:
                            # Player markets have description field with player name
                            player_name = outcome.get('description', '')
                            if player_name:
                                players_set.add(player_name)
                
                # Convert to player list format
                # Since we can't determine team from player markets, we'll split them
                players_list = list(players_set)
                mid_point = len(players_list) // 2
                
                team_a_players = [
                    {'id': f"player_{i}", 'name': name, 'role': 'Player'}
                    for i, name in enumerate(players_list[:mid_point])
                ]
                team_b_players = [
                    {'id': f"player_{i+mid_point}", 'name': name, 'role': 'Player'}
                    for i, name in enumerate(players_list[mid_point:])
                ]
                
                return {
                    'team_a_players': team_a_players,
                    'team_b_players': team_b_players
                }
            
        except Exception as e:
            logger.warning(f"Could not fetch players from odds for event {event_id}: {str(e)}")
        
        return {'team_a_players': [], 'team_b_players': []}


class EntitySportAPIService:
    """
    Production-ready service to fetch cricket data from EntitySport API
    Documentation: https://www.entitysport.com/api-doc/
    Uses token-based authentication with automatic token refresh
    """
    
    def __init__(self):
        # Production-ready: Use environment variables with fallback to defaults
        self.secret = getattr(settings, 'ENTITYSPORT_API_SECRET', '9bb7fd05727b4215593b85d2ff1afc9a')
        self.access = getattr(settings, 'ENTITYSPORT_API_ACCESS', 'edbf6c0ed9a9960a3fb8dab71fc9af54')
        self.base_url = getattr(settings, 'ENTITYSPORT_API_BASE_URL', 'https://restapi.entitysport.com/v2')
        self.timeout = 30  # Production timeout
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        # Token management
        self._token = None
        self._token_expires_at = None
        
        if not self.secret or not self.access:
            logger.warning("EntitySport API keys not configured. Set ENTITYSPORT_API_SECRET and ENTITYSPORT_API_ACCESS in settings or environment.")
    
    def _get_auth_token(self, force_refresh=False):
        """
        Get authentication token from EntitySport API
        Automatically refreshes if expired or unavailable
        Returns token string or None if failed
        """
        # Check if we have a valid token
        if not force_refresh and self._token and self._token_expires_at:
            # Check if token is still valid (with 5 minute buffer)
            buffer_time = timedelta(minutes=5)
            if timezone.now() < (self._token_expires_at - buffer_time):
                return self._token
        
        # Need to get a new token
        if not requests:
            logger.error("requests library not available")
            return None
        
        if not self.secret or not self.access:
            logger.error("EntitySport API keys not configured")
            return None
        
        try:
            url = f"{self.base_url}/auth/"
            response = requests.post(
                url,
                data={
                    'access_key': self.access,
                    'secret_key': self.secret,
                    'extend': '1'  # Token expires on subscription end date
                },
                timeout=self.timeout,
                headers={
                    'User-Agent': 'CricketDuel/1.0',
                    'Accept': 'application/json'
                }
            )
            
            if response.status_code != 200:
                logger.error(f"EntitySport Auth API error: {response.status_code} - {response.text[:200]}")
                return None
            
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.error(f"EntitySport Auth API returned error: {data.get('status', 'unknown')}")
                return None
            
            response_data = data.get('response', {})
            token = response_data.get('token')
            expires = response_data.get('expires', '')
            
            if not token:
                logger.error("No token received from EntitySport Auth API")
                return None
            
            # Parse expiration date
            if expires:
                try:
                    # Handle different expiration formats
                    if isinstance(expires, int):
                        # Unix timestamp (seconds since epoch)
                        from datetime import datetime as dt
                        self._token_expires_at = timezone.make_aware(dt.fromtimestamp(expires))
                    elif isinstance(expires, str):
                        # String format: "2025-12-31 23:59:59" or ISO format
                        if 'T' in expires:
                            self._token_expires_at = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                        else:
                            self._token_expires_at = datetime.strptime(expires, '%Y-%m-%d %H:%M:%S')
                        
                        if timezone.is_naive(self._token_expires_at):
                            self._token_expires_at = timezone.make_aware(self._token_expires_at)
                    else:
                        # Unknown format, use default
                        raise ValueError(f"Unknown expiration format: {type(expires)}")
                except (ValueError, AttributeError, TypeError, OSError) as e:
                    logger.warning(f"Could not parse token expiration date: {expires} (type: {type(expires)}), using 24 hours default. Error: {str(e)}")
                    self._token_expires_at = timezone.now() + timedelta(hours=24)
            else:
                # Default to 24 hours if no expiration provided
                self._token_expires_at = timezone.now() + timedelta(hours=24)
            
            self._token = token
            logger.info(f"Successfully obtained EntitySport API token (expires: {self._token_expires_at})")
            return token
            
        except requests.exceptions.Timeout:
            logger.error("Request timeout while getting auth token")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while getting auth token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting auth token: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    @property
    def token(self):
        """
        Get current valid token, refreshing if necessary
        """
        return self._get_auth_token()
    
    def _make_request(self, endpoint, params=None, retry_count=0):
        """
        Make HTTP request with retry logic and proper error handling
        """
        if not requests:
            logger.error("requests library not available")
            return None
        
        if not self.token:
            logger.error("EntitySport API token not configured")
            return None
        
        try:
            # Get valid token (will refresh if needed)
            current_token = self.token
            if not current_token:
                logger.error("Could not obtain valid token for EntitySport API")
                return None
            
            url = f"{self.base_url}/{endpoint}"
            request_params = {'token': current_token}
            if params:
                request_params.update(params)
            
            response = requests.get(
                url,
                params=request_params,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'CricketDuel/1.0',
                    'Accept': 'application/json'
                }
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    logger.warning(f"Rate limited. Retrying in {self.retry_delay} seconds...")
                    import time
                    time.sleep(self.retry_delay)
                    return self._make_request(endpoint, params, retry_count + 1)
                else:
                    logger.error("Max retries reached for rate limit")
                    return None
            
            # Handle other HTTP errors
            if response.status_code != 200:
                logger.error(f"EntitySport API error: {response.status_code} - {response.text[:200]}")
                # If unauthorized, try refreshing token once
                if response.status_code == 401 and retry_count == 0:
                    logger.warning("Token may be expired, attempting to refresh...")
                    self._get_auth_token(force_refresh=True)
                    return self._make_request(endpoint, params, retry_count + 1)
                return None
            
            data = response.json()
            
            # Check API response status
            if data.get('status') != 'ok':
                error_msg = data.get('status', 'unknown')
                logger.error(f"EntitySport API returned error: {error_msg}")
                # If token error, try refreshing token once
                if 'token' in error_msg.lower() or 'auth' in error_msg.lower():
                    if retry_count == 0:
                        logger.warning("Token may be invalid, attempting to refresh...")
                        self._get_auth_token(force_refresh=True)
                        return self._make_request(endpoint, params, retry_count + 1)
                return None
            
            return data.get('response', {})
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {endpoint}")
            if retry_count < self.max_retries:
                import time
                time.sleep(self.retry_delay)
                return self._make_request(endpoint, params, retry_count + 1)
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {endpoint}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching from EntitySport API: {str(e)}")
            return None
    
    def get_live_matches(self):
        """
        Fetch all live cricket matches from EntitySport API
        Uses endpoint: /matches/?status=1&token={token}
        Status: 1 = Live matches
        Returns list of formatted match dictionaries
        """
        try:
            # Fetch all live matches (status=1 means live)
            response_data = self._make_request('matches', params={'status': 1})
            if not response_data:
                logger.warning("No response data from EntitySport API for live matches")
                return []
            
            matches = response_data.get('items', [])
            if not matches:
                logger.info("No live matches found in API response")
                return []
            
            formatted = self._format_api_matches(matches)
            logger.info(f"Fetched {len(formatted)} live matches from EntitySport API")
            return formatted
            
        except Exception as e:
            logger.error(f"Error fetching live matches from EntitySport API: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_upcoming_matches(self):
        """
        Fetch upcoming cricket matches from EntitySport API
        Status: 0 = Upcoming/Scheduled
        Returns list of formatted match dictionaries
        """
        try:
            response_data = self._make_request('matches', params={'status': 0})
            if not response_data:
                return []
            
            matches = response_data.get('items', [])
            formatted = self._format_api_matches(matches)
            logger.info(f"Fetched {len(formatted)} upcoming matches from EntitySport API")
            return formatted
            
        except Exception as e:
            logger.error(f"Error fetching upcoming matches from EntitySport API: {str(e)}")
            return []
    
    def _format_api_matches(self, api_data):
        """
        Format EntitySport API response to standard format
        """
        formatted = []
        for match in api_data:
            try:
                # Extract team information
                teama = match.get('teama', {})
                teamb = match.get('teamb', {})
                
                team_a_name = teama.get('name', 'Team A')
                team_b_name = teamb.get('name', 'Team B')
                
                # Determine match status
                status_code = match.get('status', 0)
                if status_code == 1:
                    status = 'live'
                elif status_code == 2:
                    status = 'completed'
                else:
                    status = 'upcoming'
                
                # Parse match date
                date_start = match.get('date_start', '')
                if date_start:
                    try:
                        # Parse format: "2025-03-09 09:00:00"
                        match_date = datetime.strptime(date_start, '%Y-%m-%d %H:%M:%S')
                        if timezone.is_naive(match_date):
                            match_date = timezone.make_aware(match_date)
                    except (ValueError, AttributeError):
                        # Fallback to timestamp if available
                        timestamp = match.get('timestamp_start')
                        if timestamp:
                            match_date = timezone.datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        else:
                            match_date = timezone.now()
                else:
                    match_date = timezone.now()
                
                # Get venue information
                venue = match.get('venue', {})
                venue_name = venue.get('name', 'TBA') if isinstance(venue, dict) else str(venue) if venue else 'TBA'
                
                formatted.append({
                    'id': str(match.get('match_id', '')),
                    'name': match.get('title', f"{team_a_name} vs {team_b_name}"),
                    'team_a': {
                        'id': f"entitysport_team_{teama.get('team_id', '')}",
                        'name': team_a_name,
                        'short_name': teama.get('short_name', team_a_name[:3].upper()),
                        'logo_url': teama.get('logo_url', '')
                    },
                    'team_b': {
                        'id': f"entitysport_team_{teamb.get('team_id', '')}",
                        'name': team_b_name,
                        'short_name': teamb.get('short_name', team_b_name[:3].upper()),
                        'logo_url': teamb.get('logo_url', '')
                    },
                    'status': status,
                    'date': match_date.isoformat(),
                    'venue': venue_name,
                    'format': match.get('format_str', ''),
                    'competition': match.get('competition', {}).get('title', '') if isinstance(match.get('competition'), dict) else ''
                })
            except Exception as e:
                logger.warning(f"Error formatting match {match.get('match_id', 'unknown')}: {str(e)}")
                continue
        
        return formatted
    
    def get_match_details(self, match_id):
        """
        Get detailed information about a specific match
        """
        try:
            response_data = self._make_request(f'matches/{match_id}/info')
            if not response_data:
                return None
            
            match = response_data.get('match', {})
            if not match:
                return None
            
            formatted = self._format_api_matches([match])
            return formatted[0] if formatted else None
            
        except Exception as e:
            logger.error(f"Error fetching match details for {match_id}: {str(e)}")
            return None
    
    def get_match_squad(self, match_id):
        """
        Get squad/players for a match from EntitySport API
        Returns dict with team_a_players and team_b_players
        """
        try:
            response_data = self._make_request(f'matches/{match_id}/squads')
            if not response_data:
                return {'team_a_players': [], 'team_b_players': []}
            
            squad = response_data.get('squad', {})
            teama_squad = squad.get('teama', {}).get('players', [])
            teamb_squad = squad.get('teamb', {}).get('players', [])
            
            team_a_players = []
            for player in teama_squad:
                team_a_players.append({
                    'id': f"entitysport_player_{player.get('player_id', '')}",
                    'name': player.get('name', ''),
                    'role': player.get('role', 'Player')
                })
            
            team_b_players = []
            for player in teamb_squad:
                team_b_players.append({
                    'id': f"entitysport_player_{player.get('player_id', '')}",
                    'name': player.get('name', ''),
                    'role': player.get('role', 'Player')
                })
            
            return {
                'team_a_players': team_a_players,
                'team_b_players': team_b_players
            }
            
        except Exception as e:
            logger.error(f"Error fetching squad for match {match_id}: {str(e)}")
            return {'team_a_players': [], 'team_b_players': []}
    
    def get_match_live_data(self, match_id):
        """
        Get live match data for a specific match
        Endpoint: /matches/{match_id}/live
        Returns dict with live scores, current players, etc.
        """
        try:
            response_data = self._make_request(f'matches/{match_id}/live')
            if not response_data:
                return None
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error fetching live data for match {match_id}: {str(e)}")
            return None
    
    def get_match_score(self, match_id):
        """
        Get current score and player stats for a match
        Returns dict with player runs, wickets, etc.
        """
        try:
            # Try live endpoint first for real-time data
            live_data = self.get_match_live_data(match_id)
            if live_data:
                # Extract player stats from live data
                scorecard = live_data.get('scorecard', {})
                innings = scorecard.get('innings', [])
                
                player_stats = {}
                for inning in innings:
                    batting = inning.get('batting', [])
                    for batsman in batting:
                        player_id = f"entitysport_player_{batsman.get('player_id', '')}"
                        player_stats[player_id] = {
                            'runs': batsman.get('runs', 0),
                            'balls': batsman.get('balls', 0),
                            'wickets': 0
                        }
                
                if player_stats:
                    return {'player_stats': player_stats}
            
            # Fallback to scorecard endpoint
            response_data = self._make_request(f'matches/{match_id}/scorecard')
            if not response_data:
                return {}
            
            scorecard = response_data.get('scorecard', {})
            innings = scorecard.get('innings', [])
            
            player_stats = {}
            for inning in innings:
                batting = inning.get('batting', [])
                for batsman in batting:
                    player_id = f"entitysport_player_{batsman.get('player_id', '')}"
                    player_stats[player_id] = {
                        'runs': batsman.get('runs', 0),
                        'balls': batsman.get('balls', 0),
                        'wickets': 0
                    }
            
            return {'player_stats': player_stats}
            
        except Exception as e:
            logger.error(f"Error fetching scorecard for match {match_id}: {str(e)}")
            return {}


# Singleton instances
cricket_api = CricketAPIService()
odds_api = OddsAPIService()
entitysport_api = EntitySportAPIService()
