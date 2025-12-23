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
from core.services import cricket_api


class Command(BaseCommand):
    help = 'Syncs live and upcoming match data from cricket API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api',
            type=str,
            default='mock',
            help='API to use: mock, cricapi, or rapidapi (default: mock)',
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

        # For now, we'll use the service layer which has mock data
        # In production, update the service to use real APIs
        if api_type == 'mock':
            self.stdout.write(self.style.WARNING('Using mock data. For real data, configure a cricket API.'))
            self.sync_from_mock_data(update_existing)
        else:
            self.stdout.write(self.style.ERROR(f'API type "{api_type}" not yet implemented.'))
            self.stdout.write(self.style.WARNING('Please configure cricket_api in core/services.py for real API integration.'))

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


