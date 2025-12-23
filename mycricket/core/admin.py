from django.contrib import admin
from .models import (
    Team, Player, Match, PlayerMatchStats, Wallet, Transaction,
    BettingSession, PickedPlayer, Bet
)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'api_id', 'logo', 'created_at']
    search_fields = ['name', 'short_name', 'api_id']
    list_filter = ['created_at']
    fields = ['name', 'short_name', 'api_id', 'logo', 'logo_url', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'team', 'role', 'batting_average', 'strike_rate', 'api_id']
    search_fields = ['name', 'api_id']
    list_filter = ['team', 'role']
    raw_id_fields = ['team']
    fields = ['name', 'api_id', 'team', 'role', 'picture', 'batting_average', 'strike_rate']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['match_title', 'team_a', 'team_b', 'status', 'match_date', 'venue']
    search_fields = ['match_title', 'venue']
    list_filter = ['status', 'match_date']
    raw_id_fields = ['team_a', 'team_b']


@admin.register(PlayerMatchStats)
class PlayerMatchStatsAdmin(admin.ModelAdmin):
    list_display = ['player', 'match', 'runs_scored', 'balls_faced', 'wickets']
    search_fields = ['player__name', 'match__match_title']
    list_filter = ['match', 'player__team']
    raw_id_fields = ['player', 'match']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'updated_at']
    search_fields = ['user__username', 'user__email']
    list_filter = ['updated_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'balance_after', 'created_at']
    search_fields = ['user__username', 'description']
    list_filter = ['transaction_type', 'created_at']
    raw_id_fields = ['user']
    readonly_fields = ['created_at']


@admin.register(BettingSession)
class BettingSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'match', 'better_a', 'better_b', 'status', 'players_per_side', 
                    'toss_winner', 'toss_completed', 'picks_completed', 'bets_completed', 'created_at']
    search_fields = ['better_a__username', 'better_b__username', 'match__match_title']
    list_filter = ['status', 'picks_completed', 'bets_completed', 'created_at']
    raw_id_fields = ['match', 'better_a', 'better_b', 'current_turn', 'toss_winner']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PickedPlayer)
class PickedPlayerAdmin(admin.ModelAdmin):
    list_display = ['session', 'better', 'player', 'picked_at']
    search_fields = ['better__username', 'player__name']
    list_filter = ['picked_at', 'player__team']
    raw_id_fields = ['session', 'better', 'player']


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'better', 'picked_player', 'amount_per_run', 
                    'runs_scored', 'total_payout', 'is_settled', 'created_at']
    search_fields = ['better__username', 'picked_player__player__name']
    list_filter = ['is_settled', 'created_at']
    raw_id_fields = ['session', 'better', 'picked_player']
    readonly_fields = ['created_at', 'updated_at']