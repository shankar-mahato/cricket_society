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
        """Check if all players have been picked and automatically place bets"""
        total_picks_needed = self.players_per_side * 2  # players_per_side for each team
        total_picks = PickedPlayer.objects.filter(session=self).count()
        
        if total_picks >= total_picks_needed:
            self.picks_completed = True
            self.status = 'betting'
            self.current_turn = None
            self.save()
            
            # Automatically place bets for both players
            # Note: Wallet, Transaction, Bet, and PickedPlayer are defined in this same file
            # Place bet for better_a
            wallet_a, _ = Wallet.objects.get_or_create(user=self.better_a)
            if wallet_a.balance >= self.fixed_bet_amount:
                wallet_a.withdraw(self.fixed_bet_amount)
                Transaction.objects.create(
                    user=self.better_a,
                    transaction_type='bet_placed',
                    amount=self.fixed_bet_amount,
                    balance_after=wallet_a.balance,
                    description=f'Fixed bet amount for session #{self.id}'
                )
                # Create bets for all picked players
                better_a_picks = PickedPlayer.objects.filter(session=self, better=self.better_a)
                for picked_player in better_a_picks:
                    Bet.objects.get_or_create(
                        session=self,
                        better=self.better_a,
                        picked_player=picked_player,
                        defaults={
                            'amount_per_run': Decimal('0.00'),  # Not used with fixed bet
                            'insurance_percentage': Decimal('0.00'),
                            'insurance_premium': Decimal('0.00'),
                            'insured_amount': Decimal('0.00')
                        }
                    )
            
            # Place bet for better_b
            wallet_b, _ = Wallet.objects.get_or_create(user=self.better_b)
            if wallet_b.balance >= self.fixed_bet_amount:
                wallet_b.withdraw(self.fixed_bet_amount)
                Transaction.objects.create(
                    user=self.better_b,
                    transaction_type='bet_placed',
                    amount=self.fixed_bet_amount,
                    balance_after=wallet_b.balance,
                    description=f'Fixed bet amount for session #{self.id}'
                )
                # Create bets for all picked players
                better_b_picks = PickedPlayer.objects.filter(session=self, better=self.better_b)
                for picked_player in better_b_picks:
                    Bet.objects.get_or_create(
                        session=self,
                        better=self.better_b,
                        picked_player=picked_player,
                        defaults={
                            'amount_per_run': Decimal('0.00'),  # Not used with fixed bet
                            'insurance_percentage': Decimal('0.00'),
                            'insurance_premium': Decimal('0.00'),
                            'insured_amount': Decimal('0.00')
                        }
                    )
            
            # Mark bets as completed if both have sufficient balance
            better_a_bets = Bet.objects.filter(session=self, better=self.better_a).exists()
            better_b_bets = Bet.objects.filter(session=self, better=self.better_b).exists()
            if better_a_bets and better_b_bets:
                self.bets_completed = True
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


class SessionInvite(models.Model):
    """Invite for a betting session"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]
    
    session = models.ForeignKey(BettingSession, on_delete=models.CASCADE, related_name='invites')
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invites')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invites', null=True, blank=True)
    invitee_email = models.EmailField(null=True, blank=True, help_text="Email of invitee if not a registered user")
    invitee_username = models.CharField(max_length=150, null=True, blank=True, help_text="Username of invitee if registered")
    
    # Invite details
    invite_code = models.CharField(max_length=32, unique=True, db_index=True, help_text="Unique code for invite link")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, help_text="Optional message from inviter")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Invite expiration time (default 7 days)")
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invite_code']),
            models.Index(fields=['status', 'expires_at']),
        ]
    
    def __str__(self):
        invitee_name = self.invitee.username if self.invitee else (self.invitee_email or self.invitee_username or 'Unknown')
        return f"Invite from {self.inviter.username} to {invitee_name} for session #{self.session.id}"


# ==================== DISTRIBUTOR/DEALER SYSTEM MODELS ====================

class DLWallet(models.Model):
    """Separate wallet for DL users"""
    dl_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dl_wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                  validators=[MinValueValidator(Decimal('0.00'))])
    total_credited = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                         help_text="Total amount credited by Master DL")
    total_distributed = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                            help_text="Total amount distributed to end users")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"DL Wallet - {self.dl_user.username}: ₹{self.balance}"
    
    def credit(self, amount, description=""):
        """Credit amount to DL wallet"""
        self.balance += amount
        self.total_credited += amount
        self.save()
        
        # Create transaction record
        DLTransaction.objects.create(
            dl_user=self.dl_user,
            transaction_type='credit',
            amount=amount,
            balance_after=self.balance,
            description=description or f'Credited by Master DL'
        )
    
    def debit(self, amount, description=""):
        """Debit amount from DL wallet"""
        if self.balance >= amount:
            self.balance -= amount
            self.total_distributed += amount
            self.save()
            
            # Create transaction record
            DLTransaction.objects.create(
                dl_user=self.dl_user,
                transaction_type='debit',
                amount=amount,
                balance_after=self.balance,
                description=description or f'Distributed to end user'
            )
            return True
        return False
    
    def withdraw(self, amount, description=""):
        """Withdraw amount from DL wallet (by Master DL)"""
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            
            # Create transaction record
            DLTransaction.objects.create(
                dl_user=self.dl_user,
                transaction_type='debit',  # Using debit for withdrawal
                amount=amount,
                balance_after=self.balance,
                description=description or f'Withdrawn by Master DL'
            )
            return True
        return False


class DLTransaction(models.Model):
    """Transaction history for DL wallets"""
    TRANSACTION_TYPES = [
        ('credit', 'Credit from Master DL'),
        ('debit', 'Debit to End User'),
        ('refund', 'Refund'),
    ]
    
    dl_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dl_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='related_dl_transactions',
                                      help_text="End user related to this transaction")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.dl_user.username} - {self.transaction_type} - ₹{self.amount}"


class DepositRequest(models.Model):
    """End user deposit requests to DL users"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    end_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposit_requests')
    dl_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_deposit_requests',
                                help_text="DL user who will approve this request")
    amount = models.DecimalField(max_digits=12, decimal_places=2,
                                 validators=[MinValueValidator(Decimal('0.01'))])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(null=True, blank=True,
                              help_text="Remarks from DL user")
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='processed_deposit_requests')
    
    class Meta:
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.end_user.username} - ₹{self.amount} - {self.status}"
    
    def approve(self, dl_user):
        """Approve deposit request"""
        from django.utils import timezone
        
        # Check DL wallet balance
        try:
            dl_wallet = DLWallet.objects.get(dl_user=self.dl_user)
        except DLWallet.DoesNotExist:
            return False, "DL wallet not found"
        
        if dl_wallet.balance < self.amount:
            return False, "Insufficient balance in DL wallet"
        
        # Debit from DL wallet
        if not dl_wallet.debit(self.amount, f'Deposit to {self.end_user.username}'):
            return False, "Failed to debit from DL wallet"
        
        # Credit to end user wallet
        end_user_wallet, _ = Wallet.objects.get_or_create(user=self.end_user)
        end_user_wallet.deposit(self.amount)
        
        # Create transaction record
        Transaction.objects.create(
            user=self.end_user,
            transaction_type='deposit',
            amount=self.amount,
            balance_after=end_user_wallet.balance,
            description=f'Deposit approved by DL: {self.dl_user.username}'
        )
        
        # Update request status
        self.status = 'approved'
        self.processed_at = timezone.now()
        self.processed_by = dl_user
        self.save()
        
        return True, "Deposit approved successfully"
    
    def reject(self, dl_user, remarks=""):
        """Reject deposit request"""
        from django.utils import timezone
        
        self.status = 'rejected'
        self.remarks = remarks
        self.processed_at = timezone.now()
        self.processed_by = dl_user
        self.save()
        
        return True, "Deposit request rejected"
    
    def save(self, *args, **kwargs):
        if not self.invite_code:
            import secrets
            self.invite_code = secrets.token_urlsafe(24)[:32]
        
        if not self.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(days=7)
        
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if invite has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def can_be_accepted(self):
        """Check if invite can be accepted"""
        return self.status == 'pending' and not self.is_expired() and self.session.status == 'pending' and self.session.better_b == self.session.better_a
    
    def accept(self, user):
        """Accept the invite"""
        if not self.can_be_accepted():
            return False
        
        if self.invitee and user != self.invitee:
            return False
        
        # Join the session
        self.session.better_b = user
        self.session.save()
        
        # Update invite status
        self.status = 'accepted'
        self.invitee = user
        from django.utils import timezone
        self.accepted_at = timezone.now()
        self.save()
        
        return True
    
    def decline(self, user=None):
        """Decline the invite"""
        if user and self.invitee and user != self.invitee:
            return False
        
        self.status = 'declined'
        self.save()
        return True


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