"""
Django management command to sync match data from cricket APIs.
Usage: python manage.py sync_matches
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
try:
    import requests
except ImportError:
    requests = None
import json

from core.models import Team, Player, Match
from core.services import cricket_api, odds_api, entitysport_api


class Command(BaseCommand):
    help = 'Syncs live and upcoming match data from cricket API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api',
            type=str,
            default='entitysport',
            help='API to use: mock, cricapi, entitysport, or odds (default: entitysport)',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing matches instead of skipping them',
        )

    def handle(self, *args, **options):
        api_type = options['api']
        update_existing = options['update_existing']
        
        self.stdout.write(self.style.SUCCESS(f'Syncing matches from {api_type} API...'))

        if api_type == 'entitysport':
            self.sync_from_entitysport(update_existing)
        elif api_type == 'cricapi':
            self.sync_from_cricapi(update_existing)
        elif api_type == 'odds':
            self.sync_from_odds_api(update_existing)
        elif api_type == 'mock':
            self.stdout.write(self.style.WARNING('Using mock data. For real data, use --api entitysport, --api cricapi, or --api odds.'))
            self.sync_from_mock_data(update_existing)
        else:
            self.stdout.write(self.style.ERROR(f'API type "{api_type}" not yet implemented.'))
            self.stdout.write(self.style.WARNING('Available options: entitysport, cricapi, odds, mock'))

    def sync_from_mock_data(self, update_existing):
        """Sync matches from mock API data"""
        live_matches = cricket_api.get_live_matches()
        upcoming_matches = cricket_api.get_upcoming_matches()
        
        all_matches = live_matches + upcoming_matches
        matches_created = 0
        matches_updated = 0
        
        for match_data in all_matches:
            try:
                # Get or create teams
                team_a, _ = Team.objects.get_or_create(
                    api_id=match_data['team_a']['id'],
                    defaults={
                        'name': match_data['team_a']['name'],
                        'short_name': match_data['team_a'].get('short_name', match_data['team_a']['name'][:3].upper())
                    }
                )
                
                team_b, _ = Team.objects.get_or_create(
                    api_id=match_data['team_b']['id'],
                    defaults={
                        'name': match_data['team_b']['name'],
                        'short_name': match_data['team_b'].get('short_name', match_data['team_b']['name'][:3].upper())
                    }
                )
                
                # Parse match date
                match_date = datetime.fromisoformat(match_data.get('date', timezone.now().isoformat()))
                if timezone.is_naive(match_date):
                    match_date = timezone.make_aware(match_date)
                
                # Determine status
                status = match_data.get('status', 'upcoming')
                if status == 'live':
                    status = 'live'
                elif status == 'completed':
                    status = 'completed'
                else:
                    status = 'upcoming'
                
                # Create or update match
                match, created = Match.objects.get_or_create(
                    api_id=match_data['id'],
                    defaults={
                        'team_a': team_a,
                        'team_b': team_b,
                        'match_title': match_data.get('name', f"{team_a.name} vs {team_b.name}"),
                        'venue': match_data.get('venue', 'TBA'),
                        'match_date': match_date,
                        'status': status,
                    }
                )
                
                if created:
                    matches_created += 1
                    self.stdout.write(self.style.SUCCESS(f'Created match: {match.team_a.name} vs {match.team_b.name}'))
                elif update_existing:
                    match.team_a = team_a
                    match.team_b = team_b
                    match.match_title = match_data.get('name', f"{team_a.name} vs {team_b.name}")
                    match.venue = match_data.get('venue', match.venue)
                    match.match_date = match_date
                    match.status = status
                    match.save()
                    matches_updated += 1
                    self.stdout.write(self.style.SUCCESS(f'Updated match: {match.team_a.name} vs {match.team_b.name}'))
                
                # Sync players for this match
                self.sync_match_players(match, match_data['id'])
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error syncing match {match_data.get("id", "unknown")}: {str(e)}'))
                continue
        
        self.stdout.write(self.style.SUCCESS(f'\nSync complete: {matches_created} created, {matches_updated} updated'))

    def sync_from_odds_api(self, update_existing):
        """Sync matches from The Odds API"""
        self.stdout.write(self.style.SUCCESS('Fetching upcoming matches from The Odds API (next 24 hours)...'))
        
        try:
            matches_data = odds_api.get_upcoming_matches_24h()
            
            if not matches_data:
                self.stdout.write(self.style.WARNING('No matches found in the next 24 hours.'))
                return
            
            matches_created = 0
            matches_updated = 0
            
            for match_data in matches_data:
                try:
                    # Get or create teams
                    team_a, _ = Team.objects.get_or_create(
                        api_id=match_data['team_a']['id'],
                        defaults={
                            'name': match_data['team_a']['name'],
                            'short_name': match_data['team_a']['name'][:3].upper() if len(match_data['team_a']['name']) >= 3 else match_data['team_a']['name'].upper()
                        }
                    )
                    
                    team_b, _ = Team.objects.get_or_create(
                        api_id=match_data['team_b']['id'],
                        defaults={
                            'name': match_data['team_b']['name'],
                            'short_name': match_data['team_b']['name'][:3].upper() if len(match_data['team_b']['name']) >= 3 else match_data['team_b']['name'].upper()
                        }
                    )
                    
                    # Parse match date
                    match_date = datetime.fromisoformat(match_data.get('date', timezone.now().isoformat()))
                    if timezone.is_naive(match_date):
                        match_date = timezone.make_aware(match_date)
                    
                    # Create or update match
                    match, created = Match.objects.get_or_create(
                        api_id=match_data['id'],
                        defaults={
                            'team_a': team_a,
                            'team_b': team_b,
                            'match_title': match_data.get('name', f"{team_a.name} vs {team_b.name}"),
                            'venue': match_data.get('venue', 'TBA'),
                            'match_date': match_date,
                            'status': 'upcoming',
                        }
                    )
                    
                    if created:
                        matches_created += 1
                        self.stdout.write(self.style.SUCCESS(f'✓ Created match: {match.team_a.name} vs {match.team_b.name}'))
                    elif update_existing:
                        match.team_a = team_a
                        match.team_b = team_b
                        match.match_title = match_data.get('name', f"{team_a.name} vs {team_b.name}")
                        match.venue = match_data.get('venue', match.venue)
                        match.match_date = match_date
                        match.save()
                        matches_updated += 1
                        self.stdout.write(self.style.SUCCESS(f'✓ Updated match: {match.team_a.name} vs {match.team_b.name}'))
                    
                    # Sync players for this match
                    sport_key = match_data.get('sport_key', 'cricket_t20')
                    self.sync_match_players_odds(match, match_data['id'], sport_key, team_a, team_b)
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Error syncing match {match_data.get("id", "unknown")}: {str(e)}'))
                    continue
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Sync complete: {matches_created} created, {matches_updated} updated'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error syncing from Odds API: {str(e)}'))

    def sync_from_entitysport(self, update_existing):
        """Sync matches from EntitySport API (Production-ready)"""
        self.stdout.write(self.style.SUCCESS('Fetching matches from EntitySport API...'))
        
        try:
            # Get live and upcoming matches
            live_matches = entitysport_api.get_live_matches()
            upcoming_matches = entitysport_api.get_upcoming_matches()
            
            all_matches = live_matches + upcoming_matches
            
            if not all_matches:
                self.stdout.write(self.style.WARNING('No matches found from EntitySport API.'))
                return
            
            matches_created = 0
            matches_updated = 0
            matches_skipped = 0
            
            for match_data in all_matches:
                try:
                    # Skip if missing required data
                    if not match_data.get('id') or not match_data.get('team_a') or not match_data.get('team_b'):
                        matches_skipped += 1
                        continue
                    
                    # Get or create teams
                    team_a, _ = Team.objects.get_or_create(
                        api_id=match_data['team_a']['id'],
                        defaults={
                            'name': match_data['team_a']['name'],
                            'short_name': match_data['team_a'].get('short_name', match_data['team_a']['name'][:3].upper() if len(match_data['team_a']['name']) >= 3 else match_data['team_a']['name'].upper()),
                            'logo_url': match_data['team_a'].get('logo_url', '')
                        }
                    )
                    
                    # Update logo URL if available and different
                    if match_data['team_a'].get('logo_url') and team_a.logo_url != match_data['team_a']['logo_url']:
                        team_a.logo_url = match_data['team_a']['logo_url']
                        team_a.save()
                    
                    team_b, _ = Team.objects.get_or_create(
                        api_id=match_data['team_b']['id'],
                        defaults={
                            'name': match_data['team_b']['name'],
                            'short_name': match_data['team_b'].get('short_name', match_data['team_b']['name'][:3].upper() if len(match_data['team_b']['name']) >= 3 else match_data['team_b']['name'].upper()),
                            'logo_url': match_data['team_b'].get('logo_url', '')
                        }
                    )
                    
                    # Update logo URL if available and different
                    if match_data['team_b'].get('logo_url') and team_b.logo_url != match_data['team_b']['logo_url']:
                        team_b.logo_url = match_data['team_b']['logo_url']
                        team_b.save()
                    
                    # Parse match date
                    match_date_str = match_data.get('date', '')
                    if match_date_str:
                        try:
                            # Parse ISO format datetime
                            match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                            if timezone.is_naive(match_date):
                                match_date = timezone.make_aware(match_date)
                        except (ValueError, AttributeError):
                            match_date = timezone.now()
                    else:
                        match_date = timezone.now()
                    
                    # Determine status
                    status = match_data.get('status', 'upcoming')
                    if status not in ['live', 'upcoming', 'completed', 'abandoned']:
                        status = 'upcoming'
                    
                    # Create or update match
                    match, created = Match.objects.get_or_create(
                        api_id=match_data['id'],
                        defaults={
                            'team_a': team_a,
                            'team_b': team_b,
                            'match_title': match_data.get('name', f"{team_a.name} vs {team_b.name}"),
                            'venue': match_data.get('venue', 'TBA'),
                            'match_date': match_date,
                            'status': status,
                        }
                    )
                    
                    if created:
                        matches_created += 1
                        self.stdout.write(self.style.SUCCESS(f'✓ Created match: {match.team_a.name} vs {match.team_b.name} ({status})'))
                    elif update_existing:
                        match.team_a = team_a
                        match.team_b = team_b
                        match.match_title = match_data.get('name', f"{team_a.name} vs {team_b.name}")
                        match.venue = match_data.get('venue', match.venue)
                        match.match_date = match_date
                        match.status = status
                        match.save()
                        matches_updated += 1
                        self.stdout.write(self.style.SUCCESS(f'✓ Updated match: {match.team_a.name} vs {match.team_b.name} ({status})'))
                    
                    # Sync players for this match
                    self.sync_match_players_entitysport(match, match_data['id'])
                    
                    # For live matches, also fetch and store live match data
                    if status == 'live':
                        self.sync_live_match_data(match, match_data['id'])
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Error syncing match {match_data.get("id", "unknown")}: {str(e)}'))
                    continue
            
            summary = f'\n✓ Sync complete: {matches_created} created, {matches_updated} updated'
            if matches_skipped > 0:
                summary += f', {matches_skipped} skipped'
            self.stdout.write(self.style.SUCCESS(summary))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error syncing from EntitySport API: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))

    def sync_match_players_entitysport(self, match, match_id):
        """Sync players for a match from EntitySport API"""
        try:
            squad_data = entitysport_api.get_match_squad(match_id)
            
            players_synced = 0
            
            # Sync Team A players
            for player_data in squad_data.get('team_a_players', []):
                try:
                    player, created = Player.objects.get_or_create(
                        api_id=player_data['id'],
                        defaults={
                            'name': player_data['name'],
                            'team': match.team_a,
                            'role': player_data.get('role', 'Player'),
                        }
                    )
                    # Update team if changed
                    if player.team != match.team_a:
                        player.team = match.team_a
                        player.save()
                    if created:
                        players_synced += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Error syncing player {player_data.get("name", "unknown")}: {str(e)}'))
                    continue
            
            # Sync Team B players
            for player_data in squad_data.get('team_b_players', []):
                try:
                    player, created = Player.objects.get_or_create(
                        api_id=player_data['id'],
                        defaults={
                            'name': player_data['name'],
                            'team': match.team_b,
                            'role': player_data.get('role', 'Player'),
                        }
                    )
                    # Update team if changed
                    if player.team != match.team_b:
                        player.team = match.team_b
                        player.save()
                    if created:
                        players_synced += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Error syncing player {player_data.get("name", "unknown")}: {str(e)}'))
                    continue
            
            if players_synced > 0:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Synced {players_synced} players for {match.team_a.name} vs {match.team_b.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ No players found for {match.team_a.name} vs {match.team_b.name}'))
                    
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Could not sync players for match {match_id}: {str(e)}'))

    def sync_live_match_data(self, match, match_id):
        """Sync live match data and player stats from EntitySport API"""
        try:
            from core.models import PlayerMatchStats
            
            # Get live match data
            live_data = entitysport_api.get_match_live_data(match_id)
            if not live_data:
                return
            
            # Extract scorecard and player stats
            scorecard = live_data.get('scorecard', {})
            innings = scorecard.get('innings', [])
            
            players_updated = 0
            
            # Process each inning
            for inning in innings:
                batting = inning.get('batting', [])
                bowling = inning.get('bowling', [])
                
                # Process batting stats
                for batsman in batting:
                    try:
                        player_id = batsman.get('player_id')
                        if not player_id:
                            continue
                        
                        # Find player by API ID
                        player_api_id = f"entitysport_player_{player_id}"
                        try:
                            player = Player.objects.get(api_id=player_api_id)
                        except Player.DoesNotExist:
                            # Try to find by matching name (fallback)
                            player_name = batsman.get('name', '')
                            if player_name:
                                player = Player.objects.filter(name=player_name).first()
                                if not player:
                                    continue
                            else:
                                continue
                        
                        # Get or create player match stats
                        stats, created = PlayerMatchStats.objects.get_or_create(
                            player=player,
                            match=match,
                            defaults={
                                'runs_scored': batsman.get('runs', 0),
                                'balls_faced': batsman.get('balls', 0),
                                'wickets': 0
                            }
                        )
                        
                        # Update stats
                        stats.runs_scored = batsman.get('runs', 0)
                        stats.balls_faced = batsman.get('balls', 0)
                        stats.save()
                        
                        if created:
                            players_updated += 1
                        else:
                            players_updated += 1
                            
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  Error updating player stats: {str(e)}'))
                        continue
                
                # Process bowling stats (if needed)
                for bowler in bowling:
                    try:
                        player_id = bowler.get('player_id')
                        if not player_id:
                            continue
                        
                        player_api_id = f"entitysport_player_{player_id}"
                        try:
                            player = Player.objects.get(api_id=player_api_id)
                        except Player.DoesNotExist:
                            continue
                        
                        # Update wickets if available
                        stats, _ = PlayerMatchStats.objects.get_or_create(
                            player=player,
                            match=match,
                            defaults={'runs_scored': 0, 'balls_faced': 0, 'wickets': 0}
                        )
                        
                        if bowler.get('wickets'):
                            stats.wickets = bowler.get('wickets', 0)
                            stats.save()
                            
                    except Exception as e:
                        continue
            
            if players_updated > 0:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {players_updated} player stats for live match'))
                    
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Could not sync live data for match {match_id}: {str(e)}'))

    def sync_from_cricapi(self, update_existing):
        """Sync matches from CricAPI"""
        self.stdout.write(self.style.SUCCESS('Fetching matches from CricAPI...'))
        
        try:
            # Get live and upcoming matches
            live_matches = cricket_api.get_live_matches()
            upcoming_matches = cricket_api.get_upcoming_matches()
            
            all_matches = live_matches + upcoming_matches
            
            if not all_matches:
                self.stdout.write(self.style.WARNING('No matches found from CricAPI.'))
                return
            
            matches_created = 0
            matches_updated = 0
            
            for match_data in all_matches:
                try:
                    # Get or create teams
                    team_a, _ = Team.objects.get_or_create(
                        api_id=match_data['team_a']['id'],
                        defaults={
                            'name': match_data['team_a']['name'],
                            'short_name': match_data['team_a'].get('short_name', match_data['team_a']['name'][:3].upper() if len(match_data['team_a']['name']) >= 3 else match_data['team_a']['name'].upper())
                        }
                    )
                    
                    team_b, _ = Team.objects.get_or_create(
                        api_id=match_data['team_b']['id'],
                        defaults={
                            'name': match_data['team_b']['name'],
                            'short_name': match_data['team_b'].get('short_name', match_data['team_b']['name'][:3].upper() if len(match_data['team_b']['name']) >= 3 else match_data['team_b']['name'].upper())
                        }
                    )
                    
                    # Parse match date
                    match_date_str = match_data.get('date', '')
                    if match_date_str:
                        try:
                            # Parse ISO format datetime
                            match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                            if timezone.is_naive(match_date):
                                match_date = timezone.make_aware(match_date)
                        except (ValueError, AttributeError):
                            match_date = timezone.now()
                    else:
                        match_date = timezone.now()
                    
                    # Determine status
                    status = match_data.get('status', 'upcoming')
                    if status == 'live':
                        status = 'live'
                    elif status == 'completed':
                        status = 'completed'
                    else:
                        status = 'upcoming'
                    
                    # Create or update match
                    match, created = Match.objects.get_or_create(
                        api_id=match_data['id'],
                        defaults={
                            'team_a': team_a,
                            'team_b': team_b,
                            'match_title': match_data.get('name', f"{team_a.name} vs {team_b.name}"),
                            'venue': match_data.get('venue', 'TBA'),
                            'match_date': match_date,
                            'status': status,
                        }
                    )
                    
                    if created:
                        matches_created += 1
                        self.stdout.write(self.style.SUCCESS(f'✓ Created match: {match.team_a.name} vs {match.team_b.name} ({status})'))
                    elif update_existing:
                        match.team_a = team_a
                        match.team_b = team_b
                        match.match_title = match_data.get('name', f"{team_a.name} vs {team_b.name}")
                        match.venue = match_data.get('venue', match.venue)
                        match.match_date = match_date
                        match.status = status
                        match.save()
                        matches_updated += 1
                        self.stdout.write(self.style.SUCCESS(f'✓ Updated match: {match.team_a.name} vs {match.team_b.name} ({status})'))
                    
                    # Sync players for this match
                    self.sync_match_players(match, match_data['id'])
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Error syncing match {match_data.get("id", "unknown")}: {str(e)}'))
                    continue
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Sync complete: {matches_created} created, {matches_updated} updated'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error syncing from CricAPI: {str(e)}'))

    def sync_match_players_odds(self, match, event_id, sport_key, team_a, team_b):
        """Sync players for a match from The Odds API"""
        try:
            # Try to get participants first
            squad_data = odds_api.get_match_participants(event_id, sport_key)
            
            # If no participants found, try alternative method
            if not squad_data.get('team_a_players') and not squad_data.get('team_b_players'):
                self.stdout.write(self.style.WARNING(f'  No participants found via participants endpoint, trying alternative method...'))
                squad_data = odds_api.get_match_players_alternative(
                    event_id, sport_key, team_a.name, team_b.name
                )
            
            # Sync Team A players
            players_synced = 0
            for player_data in squad_data.get('team_a_players', []):
                try:
                    player, created = Player.objects.get_or_create(
                        api_id=player_data['id'],
                        defaults={
                            'name': player_data['name'],
                            'team': team_a,
                            'role': player_data.get('role', 'Player'),
                        }
                    )
                    # Update team if changed
                    if player.team != team_a:
                        player.team = team_a
                        player.save()
                    if created:
                        players_synced += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Error syncing player {player_data.get("name", "unknown")}: {str(e)}'))
                    continue
            
            # Sync Team B players
            for player_data in squad_data.get('team_b_players', []):
                try:
                    player, created = Player.objects.get_or_create(
                        api_id=player_data['id'],
                        defaults={
                            'name': player_data['name'],
                            'team': team_b,
                            'role': player_data.get('role', 'Player'),
                        }
                    )
                    # Update team if changed
                    if player.team != team_b:
                        player.team = team_b
                        player.save()
                    if created:
                        players_synced += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Error syncing player {player_data.get("name", "unknown")}: {str(e)}'))
                    continue
            
            if players_synced > 0:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Synced {players_synced} players for {match.team_a.name} vs {match.team_b.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ No players found for {match.team_a.name} vs {match.team_b.name}'))
                    
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Could not sync players for match {event_id}: {str(e)}'))

    def sync_match_players(self, match, match_api_id):
        """Sync players for a specific match"""
        try:
            squad_data = cricket_api.get_match_squad(match_api_id)
            
            # Sync Team A players
            for player_data in squad_data.get('team_a_players', []):
                player, _ = Player.objects.get_or_create(
                    api_id=player_data['id'],
                    defaults={
                        'name': player_data['name'],
                        'team': match.team_a,
                        'role': player_data.get('role', 'Player'),
                    }
                )
                # Update team if changed
                if player.team != match.team_a:
                    player.team = match.team_a
                    player.save()
            
            # Sync Team B players
            for player_data in squad_data.get('team_b_players', []):
                player, _ = Player.objects.get_or_create(
                    api_id=player_data['id'],
                    defaults={
                        'name': player_data['name'],
                        'team': match.team_b,
                        'role': player_data.get('role', 'Player'),
                    }
                )
                # Update team if changed
                if player.team != match.team_b:
                    player.team = match.team_b
                    player.save()
                    
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not sync players for match {match_api_id}: {str(e)}'))


