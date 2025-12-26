from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import random


class Team(models.Model):
    """Cricket team model"""
    api_id = models.CharField(max_length=100, unique=True, help_text="API identifier for the team")
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, null=True, blank=True)
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True, help_text="Team logo/icon")
    logo_url = models.URLField(null=True, blank=True, help_text="External logo URL (fallback)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Player(models.Model):
    """Cricket player model"""
    api_id = models.CharField(max_length=100, unique=True, help_text="API identifier for the player")
    name = models.CharField(max_length=200)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    role = models.CharField(max_length=50, null=True, blank=True, help_text="Batsman, Bowler, All-rounder")
    picture = models.ImageField(upload_to='players/', null=True, blank=True, help_text="Player profile picture")
    batting_average = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Batting average")
    strike_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Strike rate")
    is_in_playing_eleven = models.BooleanField(default=False, help_text="Whether this player is in the playing eleven for the current/upcoming match")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.team.name})"

    class Meta:
        ordering = ['name']


class Match(models.Model):
    """Cricket match model"""
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('live', 'Live'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    
    api_id = models.CharField(max_length=100, unique=True, help_text="API identifier for the match")
    team_a = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches_as_team_a')
    team_b = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches_as_team_b')
    match_title = models.CharField(max_length=300)
    venue = models.CharField(max_length=200, null=True, blank=True)
    match_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.team_a.name} vs {self.team_b.name} - {self.match_title}"

    class Meta:
        ordering = ['-match_date']


class PlayerMatchStats(models.Model):
    """Store player statistics for a specific match"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='match_stats')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='player_stats')
    runs_scored = models.IntegerField(default=0)
    balls_faced = models.IntegerField(default=0)
    wickets = models.IntegerField(default=0, null=True, blank=True)
    overs_bowled = models.DecimalField(max_digits=4, decimal_places=1, default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['player', 'match']
        ordering = ['-runs_scored']

    def __str__(self):
        return f"{self.player.name} - {self.runs_scored} runs in {self.match}"


class Wallet(models.Model):
    """User wallet to track balance"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), 
                                   validators=[MinValueValidator(Decimal('0.00'))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - ₹{self.balance}"

    def deposit(self, amount):
        """Add money to wallet"""
        self.balance += amount
        self.save()

    def withdraw(self, amount):
        """Deduct money from wallet"""
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False


class Transaction(models.Model):
    """Wallet transaction history"""
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('bet_placed', 'Bet Placed'),
        ('bet_won', 'Bet Won'),
        ('bet_lost', 'Bet Lost'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - ₹{self.amount}"


class BettingSession(models.Model):
    """Betting session between two players"""
    STATUS_CHOICES = [
        ('pending', 'Pending - Waiting for players'),
        ('picking', 'Picking Players'),
        ('betting', 'Placing Bets'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='betting_sessions')
    better_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions_as_better_a')
    better_b = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions_as_better_b')
    
    # Configuration
    players_per_side = models.IntegerField(default=5, validators=[MinValueValidator(1)],
                                           help_text="Number of players each better can pick per team")
    fixed_bet_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('100.00'),
                                          validators=[MinValueValidator(Decimal('0.01'))],
                                          help_text="Fixed bet amount for the entire session (combined bet)")
    current_turn = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='active_sessions')
    pick_order_randomized = models.BooleanField(default=False)
    
    # Toss
    toss_winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='sessions_won_toss',
                                    help_text="Player who won the toss and picks first")
    toss_completed = models.BooleanField(default=False)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    picks_completed = models.BooleanField(default=False)
    bets_completed = models.BooleanField(default=False)
    
    # Results
    better_a_total_winnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    better_b_total_winnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.better_a.username} vs {self.better_b.username} - {self.match}"

    def perform_toss(self):
        """Perform toss - randomly determine winner"""
        if not self.toss_completed:
            # Randomly decide toss winner
            self.toss_winner = random.choice([self.better_a, self.better_b])
            self.current_turn = self.toss_winner
            self.toss_completed = True
            self.pick_order_randomized = True
            self.status = 'picking'
            self.save()
            return self.toss_winner
        return self.toss_winner

    def switch_turn(self):
        """Switch turn to the other player"""
        if not self.current_turn:
            # If no current turn, set to the other player (not the one who just picked)
            # This shouldn't happen, but handle it gracefully
            if self.better_a and self.better_b:
                self.current_turn = self.better_b
        elif self.current_turn == self.better_a:
            self.current_turn = self.better_b
        elif self.current_turn == self.better_b:
            self.current_turn = self.better_a
        else:
            # Fallback: alternate between better_a and better_b
            if self.current_turn == self.better_a:
                self.current_turn = self.better_b
            else:
                self.current_turn = self.better_a
        self.save()

    def check_picks_complete(self):
        """Check if all players have been picked"""
        total_picks_needed = self.players_per_side * 2  # players_per_side for each team
        total_picks = PickedPlayer.objects.filter(session=self).count()
        
        if total_picks >= total_picks_needed:
            self.picks_completed = True
            self.status = 'betting'
            self.current_turn = None
            self.save()
            return True
        return False

    def can_pick_player(self, user, player):
        """Check if user can pick this player"""
        if self.status != 'picking':
            return False, "Picking phase is not active"
        
        if self.current_turn != user:
            return False, "It's not your turn"
        
        # Check if player is already picked by any better (prevents both betters from picking same player)
        if PickedPlayer.objects.filter(session=self, player=player).exists():
            return False, "This player is already picked. Each player can only be selected once."
        
        # Check if user has already picked their quota for this team
        team = player.team
        user_picks_for_team = PickedPlayer.objects.filter(
            session=self, 
            better=user, 
            player__team=team
        ).count()
        
        max_picks = self.players_per_side
        if user_picks_for_team >= max_picks:
            return False, f"You have already picked {max_picks} players from {team.name}"
        
        return True, "Valid pick"


class PickedPlayer(models.Model):
    """Player picked by a better in a session"""
    session = models.ForeignKey(BettingSession, on_delete=models.CASCADE, related_name='picked_players')
    better = models.ForeignKey(User, on_delete=models.CASCADE, related_name='picked_players')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='picked_in_sessions')
    picked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['session', 'player']
        ordering = ['picked_at']

    def __str__(self):
        return f"{self.better.username} picked {self.player.name} in {self.session}"


class Bet(models.Model):
    """Bet placed on a picked player"""
    session = models.ForeignKey(BettingSession, on_delete=models.CASCADE, related_name='bets')
    better = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bets')
    picked_player = models.OneToOneField(PickedPlayer, on_delete=models.CASCADE, related_name='bet')
    amount_per_run = models.DecimalField(max_digits=10, decimal_places=2, 
                                         validators=[MinValueValidator(Decimal('0.01'))],
                                         help_text="Amount to bet per run scored")
    
    # Insurance fields
    insurance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'),
                                               validators=[MinValueValidator(Decimal('0.00'))],
                                               help_text="Insurance percentage (0-20%) of bet amount")
    insurance_premium = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                            help_text="Insurance premium paid (deducted upfront)")
    insured_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                         help_text="Amount insured (insurance_percentage × estimated_payout)")
    insurance_claimed = models.BooleanField(default=False, help_text="Whether insurance was claimed")
    insurance_refunded = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                             help_text="Amount refunded from insurance")
    
    # Results
    runs_scored = models.IntegerField(null=True, blank=True, help_text="Actual runs scored")
    total_payout = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                       help_text="Total payout = runs_scored × amount_per_run")
    is_settled = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.better.username} - ₹{self.amount_per_run}/run on {self.picked_player.player.name}"

    def calculate_payout(self):
        """Calculate payout based on runs scored"""
        if self.runs_scored is not None:
            self.total_payout = Decimal(str(self.runs_scored)) * self.amount_per_run
            self.save()
            return self.total_payout
        return Decimal('0.00')
    
    def calculate_insurance(self, estimated_max_runs=100):
        """
        Calculate insurance premium and insured amount
        Premium rate is 50% of insured amount
        """
        if self.insurance_percentage <= 0:
            return Decimal('0.00'), Decimal('0.00')
        
        # Estimated maximum payout (for insurance calculation)
        estimated_max_payout = self.amount_per_run * Decimal(str(estimated_max_runs))
        
        # Insured amount = percentage of estimated max payout
        insured_amt = (estimated_max_payout * self.insurance_percentage) / Decimal('100.00')
        
        # Premium = 50% of insured amount (platform makes profit)
        premium = insured_amt * Decimal('0.50')
        
        return premium, insured_amt
    
    def should_claim_insurance(self, threshold_runs=20):
        """
        Determine if insurance should be claimed (if payout is less than threshold, representing a loss)
        
        Args:
            threshold_runs: Runs threshold below which insurance is claimed (default 20)
        
        Returns:
            bool: True if insurance should be claimed
        """
        if self.insurance_percentage <= 0:
            return False
        
        if not self.total_payout:
            return False
        
        # Insurance is claimed if payout is less than threshold (low performance = loss)
        threshold_payout = self.amount_per_run * Decimal(str(threshold_runs))
        
        if self.total_payout < threshold_payout:
            return True
        return False