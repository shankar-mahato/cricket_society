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
        self.api_key = getattr(settings, 'CRICKET_API_KEY', None)
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
                    # Example: CricAPI endpoint
                    # response = requests.get(
                    #     f"{self.base_url}/matches",
                    #     params={'apikey': self.api_key, 'offset': 0}
                    # )
                    # if response.status_code == 200:
                    #     data = response.json()
                    #     if data.get('status') == 'success':
                    #         return self._format_api_matches(data.get('data', []))
                    pass
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
            formatted.append({
                'id': match.get('unique_id', match.get('id')),
                'name': match.get('name', match.get('title', '')),
                'team_a': {
                    'id': match.get('team-1', {}).get('id') or match.get('team-1', ''),
                    'name': match.get('team-1', {}).get('name') if isinstance(match.get('team-1'), dict) else match.get('team-1', 'Team A')
                },
                'team_b': {
                    'id': match.get('team-2', {}).get('id') or match.get('team-2', ''),
                    'name': match.get('team-2', {}).get('name') if isinstance(match.get('team-2'), dict) else match.get('team-2', 'Team B')
                },
                'status': match.get('matchStarted', False) and 'live' or 'upcoming',
                'date': match.get('dateTimeGMT', match.get('date', '')),
                'venue': match.get('venue', 'TBA')
            })
        return formatted
    
    def get_upcoming_matches(self):
        """Fetch upcoming cricket matches"""
        try:
            # Mock data for demonstration
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


# Singleton instances
cricket_api = CricketAPIService()
odds_api = OddsAPIService()
