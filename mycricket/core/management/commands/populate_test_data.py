"""
Django management command to populate test data for CricketDuel application.
Usage: python manage.py populate_test_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from core.models import Team, Player, Match, Wallet, PlayerMatchStats, MatchBet, MatchBetBalance


class Command(BaseCommand):
    help = 'Populates the database with test data for teams, players, matches, and users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            MatchBetBalance.objects.all().delete()
            MatchBet.objects.all().delete()
            Match.objects.all().delete()
            Player.objects.all().delete()
            Team.objects.all().delete()
            Wallet.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write(self.style.SUCCESS('Starting to populate test data...'))

        # Create Teams
        teams_data = [
            {'api_id': 'team_ind', 'name': 'India', 'short_name': 'IND'},
            {'api_id': 'team_aus', 'name': 'Australia', 'short_name': 'AUS'},
            {'api_id': 'team_eng', 'name': 'England', 'short_name': 'ENG'},
            {'api_id': 'team_sa', 'name': 'South Africa', 'short_name': 'SA'},
            {'api_id': 'team_nz', 'name': 'New Zealand', 'short_name': 'NZ'},
            {'api_id': 'team_pak', 'name': 'Pakistan', 'short_name': 'PAK'},
        ]

        teams = {}
        for team_data in teams_data:
            team, created = Team.objects.get_or_create(
                api_id=team_data['api_id'],
                defaults={
                    'name': team_data['name'],
                    'short_name': team_data['short_name']
                }
            )
            teams[team_data['api_id']] = team
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created team: {team.name}'))

        # Create Players for India
        india_players_data = [
            {'name': 'Virat Kohli', 'role': 'Batsman', 'batting_average': 53.41, 'strike_rate': 138.15},
            {'name': 'Rohit Sharma', 'role': 'Batsman', 'batting_average': 49.27, 'strike_rate': 140.89},
            {'name': 'KL Rahul', 'role': 'Batsman', 'batting_average': 45.11, 'strike_rate': 135.15},
            {'name': 'Rishabh Pant', 'role': 'Wicketkeeper', 'batting_average': 35.89, 'strike_rate': 148.22},
            {'name': 'Hardik Pandya', 'role': 'All-rounder', 'batting_average': 31.26, 'strike_rate': 145.33},
            {'name': 'Ravindra Jadeja', 'role': 'All-rounder', 'batting_average': 29.88, 'strike_rate': 128.45},
            {'name': 'Jasprit Bumrah', 'role': 'Bowler', 'batting_average': 7.85, 'strike_rate': 78.50},
            {'name': 'Mohammed Shami', 'role': 'Bowler', 'batting_average': 9.22, 'strike_rate': 82.33},
            {'name': 'Yuzvendra Chahal', 'role': 'Bowler', 'batting_average': 8.45, 'strike_rate': 75.22},
            {'name': 'Ravichandran Ashwin', 'role': 'All-rounder', 'batting_average': 16.44, 'strike_rate': 88.55},
            {'name': 'Suryakumar Yadav', 'role': 'Batsman', 'batting_average': 42.78, 'strike_rate': 152.88},
        ]

        # Create Players for Australia
        aus_players_data = [
            {'name': 'David Warner', 'role': 'Batsman', 'batting_average': 44.59, 'strike_rate': 142.34},
            {'name': 'Steve Smith', 'role': 'Batsman', 'batting_average': 37.84, 'strike_rate': 128.95},
            {'name': 'Glenn Maxwell', 'role': 'All-rounder', 'batting_average': 29.55, 'strike_rate': 153.22},
            {'name': 'Alex Carey', 'role': 'Wicketkeeper', 'batting_average': 28.76, 'strike_rate': 126.45},
            {'name': 'Marcus Stoinis', 'role': 'All-rounder', 'batting_average': 26.22, 'strike_rate': 136.88},
            {'name': 'Pat Cummins', 'role': 'Bowler', 'batting_average': 16.82, 'strike_rate': 95.66},
            {'name': 'Mitchell Starc', 'role': 'Bowler', 'batting_average': 12.45, 'strike_rate': 88.22},
            {'name': 'Josh Hazlewood', 'role': 'Bowler', 'batting_average': 9.88, 'strike_rate': 72.33},
            {'name': 'Adam Zampa', 'role': 'Bowler', 'batting_average': 8.22, 'strike_rate': 68.55},
            {'name': 'Mitchell Marsh', 'role': 'All-rounder', 'batting_average': 30.15, 'strike_rate': 134.22},
            {'name': 'Travis Head', 'role': 'Batsman', 'batting_average': 39.88, 'strike_rate': 138.45},
        ]

        # Create Players for England
        eng_players_data = [
            {'name': 'Jos Buttler', 'role': 'Wicketkeeper', 'batting_average': 41.96, 'strike_rate': 149.22},
            {'name': 'Jonny Bairstow', 'role': 'Batsman', 'batting_average': 36.84, 'strike_rate': 142.88},
            {'name': 'Ben Stokes', 'role': 'All-rounder', 'batting_average': 35.26, 'strike_rate': 136.55},
            {'name': 'Joe Root', 'role': 'Batsman', 'batting_average': 38.22, 'strike_rate': 126.78},
            {'name': 'Moeen Ali', 'role': 'All-rounder', 'batting_average': 25.33, 'strike_rate': 128.45},
            {'name': 'Jofra Archer', 'role': 'Bowler', 'batting_average': 8.55, 'strike_rate': 92.33},
            {'name': 'Chris Woakes', 'role': 'All-rounder', 'batting_average': 18.22, 'strike_rate': 118.88},
            {'name': 'Adil Rashid', 'role': 'Bowler', 'batting_average': 7.88, 'strike_rate': 75.66},
            {'name': 'Mark Wood', 'role': 'Bowler', 'batting_average': 9.45, 'strike_rate': 85.22},
            {'name': 'Dawid Malan', 'role': 'Batsman', 'batting_average': 40.15, 'strike_rate': 144.55},
            {'name': 'Liam Livingstone', 'role': 'All-rounder', 'batting_average': 28.44, 'strike_rate': 152.33},
        ]

        # Create Players for South Africa
        sa_players_data = [
            {'name': 'Quinton de Kock', 'role': 'Wicketkeeper', 'batting_average': 38.59, 'strike_rate': 141.88},
            {'name': 'Temba Bavuma', 'role': 'Batsman', 'batting_average': 34.22, 'strike_rate': 128.45},
            {'name': 'Aiden Markram', 'role': 'Batsman', 'batting_average': 37.55, 'strike_rate': 135.22},
            {'name': 'David Miller', 'role': 'Batsman', 'batting_average': 32.88, 'strike_rate': 142.66},
            {'name': 'Heinrich Klaasen', 'role': 'Wicketkeeper', 'batting_average': 30.15, 'strike_rate': 148.22},
            {'name': 'Kagiso Rabada', 'role': 'Bowler', 'batting_average': 11.22, 'strike_rate': 88.55},
            {'name': 'Anrich Nortje', 'role': 'Bowler', 'batting_average': 8.66, 'strike_rate': 75.33},
            {'name': 'Tabraiz Shamsi', 'role': 'Bowler', 'batting_average': 7.45, 'strike_rate': 68.88},
            {'name': 'Marco Jansen', 'role': 'All-rounder', 'batting_average': 19.55, 'strike_rate': 112.45},
            {'name': 'Rassie van der Dussen', 'role': 'Batsman', 'batting_average': 36.78, 'strike_rate': 133.22},
            {'name': 'Keshav Maharaj', 'role': 'Bowler', 'batting_average': 14.22, 'strike_rate': 95.66},
        ]

        # Create all players
        all_players_data = [
            (teams['team_ind'], india_players_data),
            (teams['team_aus'], aus_players_data),
            (teams['team_eng'], eng_players_data),
            (teams['team_sa'], sa_players_data),
        ]

        players_created = 0
        for team, players_list in all_players_data:
            for i, player_data in enumerate(players_list):
                api_id = f"{team.api_id}_player_{i+1}"
                player, created = Player.objects.get_or_create(
                    api_id=api_id,
                    defaults={
                        'name': player_data['name'],
                        'team': team,
                        'role': player_data['role'],
                        'batting_average': Decimal(str(player_data['batting_average'])),
                        'strike_rate': Decimal(str(player_data['strike_rate'])),
                    }
                )
                if created:
                    players_created += 1
                    self.stdout.write(self.style.SUCCESS(f'  Created player: {player.name} ({team.name})'))

        self.stdout.write(self.style.SUCCESS(f'Created {players_created} players.'))

        # Create Matches
        matches_data = [
            {
                'api_id': 'match_1',
                'team_a': teams['team_ind'],
                'team_b': teams['team_aus'],
                'match_title': 'India vs Australia - T20 Series Match 1',
                'venue': 'Wankhede Stadium, Mumbai',
                'match_date': timezone.now() + timedelta(hours=2),
                'status': 'upcoming'
            },
            {
                'api_id': 'match_2',
                'team_a': teams['team_eng'],
                'team_b': teams['team_sa'],
                'match_title': 'England vs South Africa - ODI Series',
                'venue': 'Lord\'s Cricket Ground, London',
                'match_date': timezone.now() + timedelta(days=1),
                'status': 'upcoming'
            },
            {
                'api_id': 'match_3',
                'team_a': teams['team_ind'],
                'team_b': teams['team_eng'],
                'match_title': 'India vs England - T20 International',
                'venue': 'Eden Gardens, Kolkata',
                'match_date': timezone.now() - timedelta(hours=1),
                'status': 'live'
            },
            {
                'api_id': 'match_4',
                'team_a': teams['team_aus'],
                'team_b': teams['team_sa'],
                'match_title': 'Australia vs South Africa - Test Match',
                'venue': 'Melbourne Cricket Ground',
                'match_date': timezone.now() - timedelta(days=1),
                'status': 'completed'
            },
            {
                'api_id': 'match_5',
                'team_a': teams['team_nz'],
                'team_b': teams['team_pak'],
                'match_title': 'New Zealand vs Pakistan - T20',
                'venue': 'Basin Reserve, Wellington',
                'match_date': timezone.now() + timedelta(days=2),
                'status': 'upcoming'
            },
        ]

        matches_created = 0
        for match_data in matches_data:
            match, created = Match.objects.get_or_create(
                api_id=match_data['api_id'],
                defaults=match_data
            )
            if created:
                matches_created += 1
                self.stdout.write(self.style.SUCCESS(f'Created match: {match.team_a.name} vs {match.team_b.name}'))

        self.stdout.write(self.style.SUCCESS(f'Created {matches_created} matches.'))

        # Create PlayerMatchStats for completed match
        completed_match = Match.objects.filter(status='completed').first()
        if completed_match:
            self.stdout.write(self.style.SUCCESS('Adding player match statistics...'))
            
            # Get players from both teams
            team_a_players = Player.objects.filter(team=completed_match.team_a)[:6]
            team_b_players = Player.objects.filter(team=completed_match.team_b)[:6]
            
            stats_created = 0
            # Add stats for team A players (simulated runs)
            runs_data_a = [45, 38, 52, 28, 15, 8]  # Simulated runs scored
            for i, player in enumerate(team_a_players):
                if i < len(runs_data_a):
                    stats, created = PlayerMatchStats.objects.get_or_create(
                        player=player,
                        match=completed_match,
                        defaults={
                            'runs_scored': runs_data_a[i],
                            'balls_faced': runs_data_a[i] + 10,  # Rough estimate
                            'wickets': 0 if player.role != 'Bowler' else 2,
                        }
                    )
                    if created:
                        stats_created += 1
                        self.stdout.write(self.style.SUCCESS(f'  Added stats: {player.name} - {runs_data_a[i]} runs'))
            
            # Add stats for team B players
            runs_data_b = [62, 35, 41, 22, 18, 12]
            for i, player in enumerate(team_b_players):
                if i < len(runs_data_b):
                    stats, created = PlayerMatchStats.objects.get_or_create(
                        player=player,
                        match=completed_match,
                        defaults={
                            'runs_scored': runs_data_b[i],
                            'balls_faced': runs_data_b[i] + 10,
                            'wickets': 0 if player.role != 'Bowler' else 1,
                        }
                    )
                    if created:
                        stats_created += 1
                        self.stdout.write(self.style.SUCCESS(f'  Added stats: {player.name} - {runs_data_b[i]} runs'))
            
            self.stdout.write(self.style.SUCCESS(f'Created {stats_created} player match statistics.'))

        # Create more matches with different statuses
        additional_matches = [
            {
                'api_id': 'match_6',
                'team_a': teams['team_nz'],
                'team_b': teams['team_ind'],
                'match_title': 'New Zealand vs India - T20 International',
                'venue': 'Eden Park, Auckland',
                'match_date': timezone.now() + timedelta(days=3),
                'status': 'upcoming'
            },
            {
                'api_id': 'match_7',
                'team_a': teams['team_pak'],
                'team_b': teams['team_eng'],
                'match_title': 'Pakistan vs England - ODI Series',
                'venue': 'Gaddafi Stadium, Lahore',
                'match_date': timezone.now() + timedelta(hours=4),
                'status': 'upcoming'
            },
            {
                'api_id': 'match_8',
                'team_a': teams['team_sa'],
                'team_b': teams['team_nz'],
                'match_title': 'South Africa vs New Zealand - Test Match Day 3',
                'venue': 'SuperSport Park, Centurion',
                'match_date': timezone.now() - timedelta(hours=3),
                'status': 'live'
            },
        ]

        additional_matches_created = 0
        for match_data in additional_matches:
            match, created = Match.objects.get_or_create(
                api_id=match_data['api_id'],
                defaults=match_data
            )
            if created:
                additional_matches_created += 1
                self.stdout.write(self.style.SUCCESS(f'Created match: {match.team_a.name} vs {match.team_b.name}'))

        if additional_matches_created > 0:
            self.stdout.write(self.style.SUCCESS(f'Created {additional_matches_created} additional matches.'))

        # Create Test Users
        test_users_data = [
            {'username': 'player1', 'email': 'player1@test.com', 'password': 'testpass123'},
            {'username': 'player2', 'email': 'player2@test.com', 'password': 'testpass123'},
            {'username': 'player3', 'email': 'player3@test.com', 'password': 'testpass123'},
            {'username': 'betuser1', 'email': 'betuser1@test.com', 'password': 'testpass123'},
            {'username': 'betuser2', 'email': 'betuser2@test.com', 'password': 'testpass123'},
        ]

        users_created = 0
        wallets_created = 0
        for user_data in test_users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                }
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                users_created += 1
                self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))
                
                # Create wallet for user
                wallet, wallet_created = Wallet.objects.get_or_create(user=user)
                if wallet_created:
                    # Add initial balance to some wallets
                    if user.username in ['player1', 'betuser1']:
                        wallet.balance = Decimal('1000.00')
                        wallet.save()
                    wallets_created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {users_created} users and {wallets_created} wallets.'))

        # Create MatchBet test data
        self.stdout.write(self.style.SUCCESS('\nCreating MatchBet test data...'))
        matches = Match.objects.all()[:5]  # Use first 5 matches
        test_users = User.objects.filter(username__in=['player1', 'player2', 'betuser1', 'betuser2'])
        
        bets_created = 0
        for match in matches:
            if not test_users.exists():
                break
            
            # Create bets for different users
            for i, user in enumerate(test_users[:2]):  # Use first 2 users per match
                # Get teams for this match
                team_a = match.team_a.name
                team_b = match.team_b.name
                
                # Create BACK bet on team_a
                bet1 = MatchBet.objects.create(
                    match=match,
                    user=user,
                    selection=team_a,
                    bet_type='back',
                    odds=Decimal('1.85') + Decimal(str(i * 0.1)),
                    stake=Decimal('100.00') * (i + 1)
                )
                bets_created += 1
                
                # Create LAY bet on team_b
                bet2 = MatchBet.objects.create(
                    match=match,
                    user=user,
                    selection=team_b,
                    bet_type='lay',
                    odds=Decimal('1.95') + Decimal(str(i * 0.1)),
                    stake=Decimal('150.00') * (i + 1)
                )
                bets_created += 1
                
                # Calculate and update balances
                # BACK bet: profit = stake * (odds - 1), selection gets +profit, other gets -stake
                back_profit = bet1.stake * (bet1.odds - Decimal('1.0'))
                balance_a, _ = MatchBetBalance.objects.get_or_create(
                    match=match, user=user, selection=team_a,
                    defaults={'balance': Decimal('0.00')}
                )
                balance_a.balance += back_profit
                balance_a.save()
                
                balance_b, _ = MatchBetBalance.objects.get_or_create(
                    match=match, user=user, selection=team_b,
                    defaults={'balance': Decimal('0.00')}
                )
                balance_b.balance -= bet1.stake
                balance_b.save()
                
                # LAY bet: liability = stake * (odds - 1), selection gets -liability, other gets +stake
                lay_liability = bet2.stake * (bet2.odds - Decimal('1.0'))
                balance_b.balance -= lay_liability
                balance_b.save()
                
                balance_a.balance += bet2.stake
                balance_a.save()
        
        self.stdout.write(self.style.SUCCESS(f'Created {bets_created} MatchBet test records.'))

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('Test data populated successfully!'))
        self.stdout.write(self.style.SUCCESS('='*50))
        
        total_teams = Team.objects.count()
        total_players = Player.objects.count()
        total_matches = Match.objects.count()
        total_users = User.objects.filter(is_superuser=False).count()
        total_wallets = Wallet.objects.count()
        total_stats = PlayerMatchStats.objects.count()
        total_match_bets = MatchBet.objects.count()
        total_match_bet_balances = MatchBetBalance.objects.count()
        
        self.stdout.write(self.style.SUCCESS('\nDatabase Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Teams: {total_teams}'))
        self.stdout.write(self.style.SUCCESS(f'  Players: {total_players}'))
        self.stdout.write(self.style.SUCCESS(f'  Matches: {total_matches}'))
        self.stdout.write(self.style.SUCCESS(f'  Users: {total_users}'))
        self.stdout.write(self.style.SUCCESS(f'  Match Bets: {total_match_bets}'))
        self.stdout.write(self.style.SUCCESS(f'  Match Bet Balances: {total_match_bet_balances}'))
        self.stdout.write(self.style.SUCCESS(f'  Wallets: {total_wallets}'))
        self.stdout.write(self.style.SUCCESS(f'  Player Match Stats: {total_stats}'))
        
        self.stdout.write(self.style.SUCCESS('\nTest Users (all passwords: testpass123):'))
        for user_data in test_users_data:
            wallet = Wallet.objects.filter(user__username=user_data['username']).first()
            balance_info = f' (Balance: ₹{wallet.balance})' if wallet and wallet.balance > 0 else ''
            self.stdout.write(self.style.SUCCESS(f'  • {user_data["username"]}{balance_info}'))
        
        self.stdout.write(self.style.SUCCESS('\nMatch Statuses:'))
        upcoming = Match.objects.filter(status='upcoming').count()
        live = Match.objects.filter(status='live').count()
        completed = Match.objects.filter(status='completed').count()
        self.stdout.write(self.style.SUCCESS(f'  Upcoming: {upcoming} | Live: {live} | Completed: {completed}'))
        
        self.stdout.write(self.style.SUCCESS('\nYou can now login and test the application!'))


