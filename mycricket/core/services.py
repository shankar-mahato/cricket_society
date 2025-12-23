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
from datetime import datetime
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

# Singleton instance
cricket_api = CricketAPIService()
