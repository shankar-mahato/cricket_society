from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.db import transaction as db_transaction
from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from .models import (
    Match, Team, Player, Wallet, BettingSession, PickedPlayer, Bet,
    Transaction, PlayerMatchStats, SessionInvite, DLWallet, DLTransaction, DepositRequest,
    MatchBet, MatchBetBalance
)
from .services import cricket_api, entitysport_api


@login_required
def home(request):
    """Home page showing live and upcoming matches - redirects based on user type"""
    from accounts.models import UserProfile
    
    # Check user type and redirect accordingly
    if request.user.is_superuser or request.user.is_staff:
        # Master DL (Superuser) - redirect to Master DL dashboard
        return redirect('core:master_dl_dashboard')
    
    # Check if user has profile
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
        if profile.user_type == 'dl':
            # DL User - redirect to DL home
            return redirect('core:dl_home')
        # End users continue to home page
    
    # Get matches from database (synced from API)
    live_matches = Match.objects.filter(status='live').order_by('-match_date')
    
    # Get upcoming matches for next 24 hours only
    now = timezone.now()
    next_24h = now + timedelta(hours=24)
    upcoming_matches = Match.objects.filter(
        status='upcoming',
        match_date__gte=now,
        match_date__lte=next_24h
    ).order_by('match_date')
    
    # Get user's active sessions
    active_sessions = BettingSession.objects.filter(
        better_a=request.user
    ) | BettingSession.objects.filter(
        better_b=request.user
    )
    active_sessions = active_sessions.exclude(status='completed').exclude(status='cancelled').select_related('better_a', 'better_b')
    
    # Ensure profiles exist for all users in active sessions
    for session in active_sessions:
        UserProfile.objects.get_or_create(user=session.better_a)
        if session.better_b != session.better_a:
            UserProfile.objects.get_or_create(user=session.better_b)
    
    # Get pending invites for the user
    pending_invites_count = SessionInvite.objects.filter(
        invitee=request.user,
        status='pending'
    ).exclude(expires_at__lt=timezone.now()).count()
    
    # Also count email invites
    email_invites_count = SessionInvite.objects.filter(
        invitee_email=request.user.email,
        status='pending',
        invitee__isnull=True
    ).exclude(expires_at__lt=timezone.now()).count()
    
    total_pending_invites = pending_invites_count + email_invites_count
    
    context = {
        'live_matches': live_matches,
        'upcoming_matches': upcoming_matches,
        'active_sessions': active_sessions,
        'pending_invites_count': total_pending_invites,
    }
    return render(request, 'core/home.html', context)


@login_required
def match_detail(request, match_id):
    """Match detail page with players and create session option"""
    match = get_object_or_404(Match, id=match_id)
    
    # Get players for both teams
    team_a_players = Player.objects.filter(team=match.team_a)
    team_b_players = Player.objects.filter(team=match.team_b)
    
    # Check if user has existing session for this match
    existing_session = BettingSession.objects.filter(
        match=match
    ).filter(
        better_a=request.user
    ) | BettingSession.objects.filter(
        match=match, better_b=request.user
    )
    existing_session = existing_session.exclude(status='completed').exclude(status='cancelled').first()
    
    # Get active sessions for this match (where user can join)
    # Sessions where better_b is same as better_a (waiting for someone to join)
    available_sessions = BettingSession.objects.filter(
        match=match,
        status='pending',
        better_b=F('better_a')  # better_b is placeholder (same as better_a)
    ).exclude(better_a=request.user)
    
    # Match Odds Data (Runner - teams with back/lay odds)
    # For now, we'll use placeholder data structure (same as DL view)
    match_odds = [
        {
            'runner': match.team_a.name,
            'back_odds': '1.85',  # Placeholder
            'lay_odds': '1.90',   # Placeholder
        },
        {
            'runner': match.team_b.name,
            'back_odds': '1.95',  # Placeholder
            'lay_odds': '2.00',   # Placeholder
        },
    ]
    
    # Session Details (like "20 overs runs adv" etc)
    session_details = [
        {'label': '20 Overs Runs Adv', 'not': '1.85', 'yes': '1.95'},
        {'label': 'Total Runs Over', 'not': '1.80', 'yes': '2.00'},
        {'label': 'Total Runs Under', 'not': '1.90', 'yes': '1.85'},
    ]
    
    context = {
        'match': match,
        'team_a_players': team_a_players,
        'team_b_players': team_b_players,
        'existing_session': existing_session,
        'available_sessions': available_sessions,
        'match_odds': match_odds,
        'session_details': session_details,
    }
    return render(request, 'core/match_detail.html', context)


@login_required
@require_http_methods(["POST"])
def create_betting_session(request, match_id):
    """Create a new betting session"""
    match = get_object_or_404(Match, id=match_id)
    
    if match.status not in ['live', 'upcoming']:
        messages.error(request, "Cannot create session for this match status")
        return redirect('core:match_detail', match_id=match_id)
    
    players_per_side = int(request.POST.get('players_per_side', 5))
    if players_per_side < 1 or players_per_side > 11:
        messages.error(request, "Players per side must be between 1 and 11")
        return redirect('core:match_detail', match_id=match_id)
    
    fixed_bet_amount = Decimal(str(request.POST.get('fixed_bet_amount', 100)))
    if fixed_bet_amount <= 0:
        messages.error(request, "Bet amount must be greater than 0")
        return redirect('core:match_detail', match_id=match_id)
    
    # Check if user already has an active session for this match
    existing = BettingSession.objects.filter(
        match=match
    ).filter(
        better_a=request.user
    ) | BettingSession.objects.filter(
        match=match, better_b=request.user
    )
    existing = existing.exclude(status='completed').exclude(status='cancelled')
    
    if existing.exists():
        messages.info(request, "You already have an active session for this match")
        return redirect('core:session_detail', session_id=existing.first().id)
    
    # Create session (waiting for another player to join)
    session = BettingSession.objects.create(
        match=match,
        better_a=request.user,
        better_b=request.user,  # Placeholder, will be updated when someone joins
        players_per_side=players_per_side,
        fixed_bet_amount=fixed_bet_amount,
        status='pending'
    )
    
    messages.success(request, "Betting session created! Waiting for another player to join.")
    return redirect('core:session_detail', session_id=session.id)


@login_required
@require_http_methods(["POST"])
def join_betting_session(request, session_id):
    """Join an existing betting session as better_b"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    if session.status != 'pending':
        messages.error(request, "This session is not available to join")
        return redirect('core:session_detail', session_id=session_id)
    
    if session.better_a == request.user:
        messages.error(request, "You cannot join your own session")
        return redirect('core:session_detail', session_id=session_id)
    
    if session.better_b != session.better_a:  # Already has a better_b
        messages.error(request, "This session is already full")
        return redirect('core:match_detail', match_id=session.match.id)
    
    # Join as better_b
    session.better_b = request.user
    session.save()
    
    messages.success(request, "You joined the session! Now perform the toss to determine who picks first.")
    return redirect('core:session_detail', session_id=session.id)


@login_required
def session_detail(request, session_id):
    """View betting session details"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    # Check if user is part of this session
    if session.better_a != request.user and session.better_b != request.user:
        messages.error(request, "You are not authorized to view this session")
        return redirect('core:home')
    
    # Ensure profiles exist for both users
    from accounts.models import UserProfile
    UserProfile.objects.get_or_create(user=session.better_a)
    if session.better_b != session.better_a:
        UserProfile.objects.get_or_create(user=session.better_b)
    
    # Get picked players
    better_a_picks_qs = PickedPlayer.objects.filter(session=session, better=session.better_a).select_related('player', 'player__team')
    better_b_picks_qs = PickedPlayer.objects.filter(session=session, better=session.better_b).select_related('player', 'player__team')
    
    # Count picks per team for each better (before converting to list)
    better_a_team_a_count = better_a_picks_qs.filter(player__team=session.match.team_a).count()
    better_a_team_b_count = better_a_picks_qs.filter(player__team=session.match.team_b).count()
    better_b_team_a_count = better_b_picks_qs.filter(player__team=session.match.team_a).count()
    better_b_team_b_count = better_b_picks_qs.filter(player__team=session.match.team_b).count()
    
    # Get bets with picked player info
    better_a_bets = Bet.objects.filter(session=session, better=session.better_a).select_related('picked_player', 'picked_player__player')
    better_b_bets = Bet.objects.filter(session=session, better=session.better_b).select_related('picked_player', 'picked_player__player')
    
    # Create bet lookup dicts for easier template access
    better_a_bets_dict = {bet.picked_player_id: bet for bet in better_a_bets}
    better_b_bets_dict = {bet.picked_player_id: bet for bet in better_b_bets}
    
    # Convert to list first
    better_a_picks = list(better_a_picks_qs)
    better_b_picks = list(better_b_picks_qs)
    
    # Add bet info to picks for template
    for pick in better_a_picks:
        pick.bet = better_a_bets_dict.get(pick.id)
    for pick in better_b_picks:
        pick.bet = better_b_bets_dict.get(pick.id)
    
    # Add match stats to picks for completed sessions (after converting to list)
    if session.status == 'completed':
        # Pre-fetch all PlayerMatchStats for this match to avoid N+1 queries
        player_stats_dict = {}
        for stats in PlayerMatchStats.objects.filter(match=session.match):
            player_stats_dict[stats.player_id] = stats
        
        for pick in better_a_picks:
            # First try to get runs from Bet model (which should have runs_scored after settlement)
            runs_scored = 0
            if pick.bet and pick.bet.runs_scored is not None:
                runs_scored = pick.bet.runs_scored
            
            # Get balls_faced from PlayerMatchStats
            balls_faced = 0
            if pick.player_id in player_stats_dict:
                stats = player_stats_dict[pick.player_id]
                balls_faced = stats.balls_faced
                # If runs not in Bet, use PlayerMatchStats
                if runs_scored == 0:
                    runs_scored = stats.runs_scored
            
            pick.runs_scored = runs_scored
            pick.balls_faced = balls_faced
            pick.player_value = Decimal(str(runs_scored)) * session.fixed_bet_amount if session.fixed_bet_amount else Decimal('0.00')
        
        # Sort picks by runs_scored (highest first) for completed sessions
        better_a_picks.sort(key=lambda x: getattr(x, 'runs_scored', 0) or 0, reverse=True)
        
        for pick in better_b_picks:
            # First try to get runs from Bet model (which should have runs_scored after settlement)
            runs_scored = 0
            if pick.bet and pick.bet.runs_scored is not None:
                runs_scored = pick.bet.runs_scored
            
            # Get balls_faced from PlayerMatchStats
            balls_faced = 0
            if pick.player_id in player_stats_dict:
                stats = player_stats_dict[pick.player_id]
                balls_faced = stats.balls_faced
                # If runs not in Bet, use PlayerMatchStats
                if runs_scored == 0:
                    runs_scored = stats.runs_scored
            
            pick.runs_scored = runs_scored
            pick.balls_faced = balls_faced
            pick.player_value = Decimal(str(runs_scored)) * session.fixed_bet_amount if session.fixed_bet_amount else Decimal('0.00')
        
        # Sort picks by runs_scored (highest first) for completed sessions
        better_b_picks.sort(key=lambda x: getattr(x, 'runs_scored', 0) or 0, reverse=True)
    
    # Get available players (not yet picked)
    picked_player_ids = PickedPlayer.objects.filter(session=session).values_list('player_id', flat=True)
    available_players = Player.objects.filter(
        team__in=[session.match.team_a, session.match.team_b]
    ).exclude(id__in=picked_player_ids)
    
    # Group by team
    team_a_available = available_players.filter(team=session.match.team_a)
    team_b_available = available_players.filter(team=session.match.team_b)
    
    # Calculate total runs and values for each better
    # For completed sessions: use Bet model
    # For live matches: fetch from API or PlayerMatchStats
    better_a_total_runs = 0
    better_b_total_runs = 0
    better_a_total_value = Decimal('0.00')
    better_b_total_value = Decimal('0.00')
    winner = None
    difference = Decimal('0.00')
    current_leader = None
    
    if session.status == 'completed':
        # For completed sessions, use Bet model
        better_a_bets_list = list(better_a_bets)
        better_b_bets_list = list(better_b_bets)
        
        for bet in better_a_bets_list:
            if bet.runs_scored is not None:
                better_a_total_runs += bet.runs_scored
        
        for bet in better_b_bets_list:
            if bet.runs_scored is not None:
                better_b_total_runs += bet.runs_scored
        
        # Calculate total values (runs × bet_amount) - only if fixed_bet_amount exists
        if session.fixed_bet_amount:
            better_a_total_value = Decimal(str(better_a_total_runs)) * session.fixed_bet_amount
            better_b_total_value = Decimal(str(better_b_total_runs)) * session.fixed_bet_amount
            
            # Calculate difference
            difference = abs(better_a_total_value - better_b_total_value)
        
        # Determine winner
        if better_a_total_value > better_b_total_value:
            winner = session.better_a
        elif better_b_total_value > better_a_total_value:
            winner = session.better_b
        # else: tie (winner is None)
    elif session.match.status == 'live':
        # For live matches, fetch current stats from API first, then PlayerMatchStats
        api_player_stats = {}
        try:
            # Try EntitySport API first (production API), then fallback to cricket_api
            score_data = None
            try:
                score_data = entitysport_api.get_match_score(session.match.api_id)
            except Exception:
                pass
            
            if not score_data:
                try:
                    score_data = cricket_api.get_match_score(session.match.api_id)
                except Exception:
                    pass
            
            if score_data:
                api_player_stats = score_data.get('player_stats', {})
        except Exception:
            # If API fails, continue with PlayerMatchStats
            pass
        
        # Pre-fetch all PlayerMatchStats for this match as fallback
        player_stats_dict = {}
        for stats in PlayerMatchStats.objects.filter(match=session.match):
            player_stats_dict[stats.player_id] = stats
        
        # Calculate current totals from API or PlayerMatchStats and add stats to picks
        for pick in better_a_picks:
            runs = 0
            balls = 0
            # First try API (check multiple key formats)
            if pick.player.api_id:
                api_id_str = str(pick.player.api_id)
                # Try exact string match
                if api_id_str in api_player_stats:
                    player_stat = api_player_stats[api_id_str]
                    if isinstance(player_stat, dict):
                        runs = player_stat.get('runs', 0)
                        balls = player_stat.get('balls', 0)
                else:
                    # Try integer key only if api_id is numeric
                    try:
                        api_id_int = int(pick.player.api_id)
                        if api_id_int in api_player_stats:
                            player_stat = api_player_stats[api_id_int]
                            if isinstance(player_stat, dict):
                                runs = player_stat.get('runs', 0)
                                balls = player_stat.get('balls', 0)
                    except (ValueError, TypeError):
                        # api_id is not numeric, try partial matching
                        for key, value in api_player_stats.items():
                            key_str = str(key)
                            if key_str == api_id_str or key_str.endswith(api_id_str) or api_id_str in key_str:
                                player_stat = value
                                if isinstance(player_stat, dict):
                                    runs = player_stat.get('runs', 0)
                                    balls = player_stat.get('balls', 0)
                                break
            
            # Fallback to PlayerMatchStats
            if runs == 0 and pick.player_id in player_stats_dict:
                stats = player_stats_dict[pick.player_id]
                runs = stats.runs_scored
                balls = stats.balls_faced
            
            # Add stats to pick object for template
            pick.runs_scored = runs
            pick.balls_faced = balls
            pick.player_value = Decimal(str(runs)) * session.fixed_bet_amount if session.fixed_bet_amount else Decimal('0.00')
            pick.has_batted = runs > 0 or balls > 0
            pick.is_active = balls > 0  # Currently playing if they have faced balls
            
            better_a_total_runs += runs
        
        for pick in better_b_picks:
            runs = 0
            balls = 0
            # First try API (check multiple key formats)
            if pick.player.api_id:
                api_id_str = str(pick.player.api_id)
                # Try exact string match
                if api_id_str in api_player_stats:
                    player_stat = api_player_stats[api_id_str]
                    if isinstance(player_stat, dict):
                        runs = player_stat.get('runs', 0)
                        balls = player_stat.get('balls', 0)
                else:
                    # Try integer key only if api_id is numeric
                    try:
                        api_id_int = int(pick.player.api_id)
                        if api_id_int in api_player_stats:
                            player_stat = api_player_stats[api_id_int]
                            if isinstance(player_stat, dict):
                                runs = player_stat.get('runs', 0)
                                balls = player_stat.get('balls', 0)
                    except (ValueError, TypeError):
                        # api_id is not numeric, try partial matching
                        for key, value in api_player_stats.items():
                            key_str = str(key)
                            if key_str == api_id_str or key_str.endswith(api_id_str) or api_id_str in key_str:
                                player_stat = value
                                if isinstance(player_stat, dict):
                                    runs = player_stat.get('runs', 0)
                                    balls = player_stat.get('balls', 0)
                                break
            
            # Fallback to PlayerMatchStats
            if runs == 0 and pick.player_id in player_stats_dict:
                stats = player_stats_dict[pick.player_id]
                runs = stats.runs_scored
                balls = stats.balls_faced
            
            # Add stats to pick object for template
            pick.runs_scored = runs
            pick.balls_faced = balls
            pick.player_value = Decimal(str(runs)) * session.fixed_bet_amount if session.fixed_bet_amount else Decimal('0.00')
            pick.has_batted = runs > 0 or balls > 0
            pick.is_active = balls > 0  # Currently playing if they have faced balls
            
            better_b_total_runs += runs
        
        # Calculate current values
        if session.fixed_bet_amount:
            better_a_total_value = Decimal(str(better_a_total_runs)) * session.fixed_bet_amount
            better_b_total_value = Decimal(str(better_b_total_runs)) * session.fixed_bet_amount
            difference = abs(better_a_total_value - better_b_total_value)
        
        # Determine current leader
        if better_a_total_value > better_b_total_value:
            current_leader = session.better_a
        elif better_b_total_value > better_a_total_value:
            current_leader = session.better_b
        # else: tie (current_leader is None)
        
        # Sort picks: active players first, then batted players, then yet to bat
        # Sort by: is_active (desc), has_batted (desc), runs_scored (desc)
        better_a_picks.sort(key=lambda x: (getattr(x, 'is_active', False), getattr(x, 'has_batted', False), getattr(x, 'runs_scored', 0)), reverse=True)
        better_b_picks.sort(key=lambda x: (getattr(x, 'is_active', False), getattr(x, 'has_batted', False), getattr(x, 'runs_scored', 0)), reverse=True)
    
    context = {
        'session': session,
        'better_a_picks': better_a_picks,
        'better_b_picks': better_b_picks,
        'better_a_bets': better_a_bets,
        'better_b_bets': better_b_bets,
        'team_a_available': team_a_available,
        'team_b_available': team_b_available,
        'better_a_team_a_count': better_a_team_a_count,
        'better_a_team_b_count': better_a_team_b_count,
        'better_b_team_a_count': better_b_team_a_count,
        'better_b_team_b_count': better_b_team_b_count,
        'is_my_turn': session.current_turn == request.user if session.current_turn else False,
        'toss_completed': session.toss_completed,
        'toss_winner': session.toss_winner,
        'can_perform_toss': session.status == 'pending' and session.better_b != session.better_a,
        'better_a_total_runs': better_a_total_runs,
        'better_b_total_runs': better_b_total_runs,
        'better_a_total_value': better_a_total_value,
        'better_b_total_value': better_b_total_value,
        'difference': difference,
        'winner': winner,
        'current_leader': current_leader,
    }
    return render(request, 'core/session_detail.html', context)


@login_required
@require_http_methods(["POST"])
def perform_toss(request, session_id):
    """Perform toss to determine who picks first"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    # Check if user is part of this session
    if session.better_a != request.user and session.better_b != request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        messages.error(request, "You are not authorized to perform toss for this session")
        return redirect('core:session_detail', session_id=session_id)
    
    # Check if both players have joined
    if session.better_b == session.better_a:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Waiting for another player to join'})
        messages.error(request, "Waiting for another player to join")
        return redirect('core:session_detail', session_id=session_id)
    
    # Check if toss already completed
    if session.toss_completed:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'already_completed': True,
                'toss_winner': session.toss_winner.username if session.toss_winner else None,
                'current_turn': session.current_turn.username if session.current_turn else None,
                'status': session.status
            })
        messages.info(request, "Toss already completed")
        return redirect('core:session_detail', session_id=session_id)
    
    # Perform toss
    toss_winner = session.perform_toss()
    session.refresh_from_db()
    
    # Return JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'toss_winner': toss_winner.username,
            'toss_winner_id': toss_winner.id,
            'current_turn': session.current_turn.username if session.current_turn else None,
            'current_turn_id': session.current_turn.id if session.current_turn else None,
            'is_my_turn': session.current_turn == request.user if session.current_turn else False,
            'status': session.status,
            'updated_at': session.updated_at.isoformat()
        })
    
    messages.success(request, f"Toss completed! {toss_winner.username} won the toss and will pick first!")
    return redirect('core:session_detail', session_id=session_id)


@login_required
@require_http_methods(["POST"])
def pick_player(request, session_id):
    """Pick a player in the betting session"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    if session.better_a != request.user and session.better_b != request.user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        player_id = data.get('player_id')
        
        if not player_id:
            return JsonResponse({'success': False, 'error': 'Player ID required'})
        
        player = get_object_or_404(Player, id=player_id)
        
        # Validate pick - ensures same player cannot be picked by both betters
        can_pick, error_msg = session.can_pick_player(request.user, player)
        if not can_pick:
            return JsonResponse({'success': False, 'error': error_msg})
        
        # Check again if player was just picked (race condition protection)
        if PickedPlayer.objects.filter(session=session, player=player).exists():
            return JsonResponse({'success': False, 'error': 'This player was just picked by the other player. Please select another player.'})
        
        # Create picked player with database constraint as final safeguard
        try:
            with db_transaction.atomic():
                picked_player = PickedPlayer.objects.create(
                    session=session,
                    better=request.user,
                    player=player
                )
                
                # Refresh session from database to get latest state
                session.refresh_from_db()
                
                # Switch turn (only if picking is not complete)
                if not session.picks_completed:
                    session.switch_turn()
                    session.save()
                
                # Check if picking is complete (this may change status)
                session.check_picks_complete()
                
                # Refresh again to get updated status
                session.refresh_from_db()
        except IntegrityError:
            return JsonResponse({'success': False, 'error': 'This player was already picked. Please select another player.'})
        
        # Get updated pick counts for both betters
        better_a_picks = PickedPlayer.objects.filter(session=session, better=session.better_a).count()
        better_b_picks = PickedPlayer.objects.filter(session=session, better=session.better_b).count()
        
        return JsonResponse({
            'success': True,
            'message': f'Picked {player.name}',
            'picks_completed': session.picks_completed,
            'current_turn': session.current_turn.username if session.current_turn else None,
            'current_turn_id': session.current_turn.id if session.current_turn else None,
            'session_status': session.status,
            'is_my_turn': session.current_turn == request.user if session.current_turn else False,
            'updated_at': session.updated_at.isoformat(),
            'better_a_picks_count': better_a_picks,
            'better_b_picks_count': better_b_picks,
            'picked_player_name': player.name
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def place_bet(request, session_id):
    """Place fixed bet amount for the session"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    if session.better_a != request.user and session.better_b != request.user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if session.status != 'betting':
        return JsonResponse({'success': False, 'error': 'Betting phase is not active'})
    
    try:
        # Get or create wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        # Check if user has already placed bet
        user_bets = Bet.objects.filter(session=session, better=request.user)
        if user_bets.exists():
            return JsonResponse({'success': False, 'error': 'You have already placed your bet for this session'})
        
        # Check if user has enough balance
        if wallet.balance < session.fixed_bet_amount:
            return JsonResponse({
                'success': False,
                'error': f'Insufficient balance. Required: ₹{session.fixed_bet_amount}, Your balance: ₹{wallet.balance}'
            })
        
        # Deduct bet amount from wallet
        wallet.withdraw(session.fixed_bet_amount)
        Transaction.objects.create(
            user=request.user,
            transaction_type='bet_placed',
            amount=session.fixed_bet_amount,
            balance_after=wallet.balance,
            description=f'Fixed bet amount for session #{session.id}'
        )
        
        # Create bet records for all picked players (using fixed bet amount)
        user_picks = PickedPlayer.objects.filter(session=session, better=request.user)
        for picked_player in user_picks:
            # Calculate amount per run based on fixed bet amount
            # Distribute fixed amount equally across all picks
            amount_per_run = session.fixed_bet_amount / Decimal(str(user_picks.count()))
            
            Bet.objects.create(
                session=session,
                better=request.user,
                picked_player=picked_player,
                amount_per_run=amount_per_run,
                insurance_percentage=Decimal('0.00'),
                insurance_premium=Decimal('0.00'),
                insured_amount=Decimal('0.00')
            )
        
        # Check if both betters have placed bets
        better_a_bets = Bet.objects.filter(session=session, better=session.better_a).exists()
        better_b_bets = Bet.objects.filter(session=session, better=session.better_b).exists()
        
        if better_a_bets and better_b_bets:
            session.bets_completed = True
            session.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Bet placed: ₹{session.fixed_bet_amount} (distributed across {user_picks.count()} players)',
            'bets_completed': session.bets_completed
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def wallet_view(request):
    """View wallet and transaction history"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:50]
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'core/wallet.html', context)


@login_required
@require_http_methods(["POST"])
def deposit_wallet(request):
    """Deposit money to wallet"""
    try:
        amount = Decimal(str(request.POST.get('amount', 0)))
        if amount <= 0:
            messages.error(request, "Amount must be greater than 0")
            return redirect('core:wallet')
        
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        with db_transaction.atomic():
            wallet.deposit(amount)
            Transaction.objects.create(
                user=request.user,
                transaction_type='deposit',
                amount=amount,
                balance_after=wallet.balance,
                description=f'Deposit of ₹{amount}'
            )
        
        messages.success(request, f'Successfully deposited ₹{amount}')
        return redirect('core:wallet')
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('core:wallet')


@login_required
def settle_session(request, session_id):
    """Settle bets and calculate winnings after match ends"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    if session.status == 'completed':
        messages.info(request, "Session already settled")
        return redirect('core:session_detail', session_id=session_id)
    
    if session.match.status != 'completed':
        messages.error(request, "Match is not completed yet")
        return redirect('core:session_detail', session_id=session_id)
    
    # Fetch player stats from API
    # Try EntitySport API first (production API), then fallback to cricket_api
    score_data = None
    try:
        score_data = entitysport_api.get_match_score(session.match.api_id)
    except Exception:
        pass
    
    if not score_data:
        try:
            score_data = cricket_api.get_match_score(session.match.api_id)
        except Exception:
            pass
    
    player_stats = score_data.get('player_stats', {}) if score_data else {}
    
    better_a_total_runs = 0
    better_b_total_runs = 0
    
    with db_transaction.atomic():
        # Process all bets and calculate total runs
        bets = Bet.objects.filter(session=session, is_settled=False)
        
        for bet in bets:
            player_api_id = bet.picked_player.player.api_id
            player_stat = player_stats.get(player_api_id, {})
            runs_scored = player_stat.get('runs', 0)
            balls_faced = player_stat.get('balls', 0)
            
            # Update bet with runs scored
            bet.runs_scored = runs_scored
            bet.calculate_payout()
            bet.is_settled = True
            bet.save()
            
            # Update player match stats
            PlayerMatchStats.objects.update_or_create(
                player=bet.picked_player.player,
                match=session.match,
                defaults={
                    'runs_scored': runs_scored,
                    'balls_faced': balls_faced
                }
            )
            
            # Add runs to respective better's total
            if bet.better == session.better_a:
                better_a_total_runs += runs_scored
            else:
                better_b_total_runs += runs_scored
        
        # Calculate total value: (total_runs × bet_amount) for each better
        better_a_total_value = Decimal(str(better_a_total_runs)) * session.fixed_bet_amount
        better_b_total_value = Decimal(str(better_b_total_runs)) * session.fixed_bet_amount
        
        # Calculate difference
        difference = abs(better_a_total_value - better_b_total_value)
        
        # Determine winner (player with higher total value)
        winner = None
        winner_winnings = Decimal('0.00')
        
        if better_a_total_value > better_b_total_value:
            winner = session.better_a
            winner_winnings = difference
            session.better_a_total_winnings = difference
            session.better_b_total_winnings = Decimal('0.00')
        elif better_b_total_value > better_a_total_value:
            winner = session.better_b
            winner_winnings = difference
            session.better_a_total_winnings = Decimal('0.00')
            session.better_b_total_winnings = difference
        else:
            # Tie - no winner, no winnings
            winner = None
            session.better_a_total_winnings = Decimal('0.00')
            session.better_b_total_winnings = Decimal('0.00')
        
        # Store winner and totals
        session.status = 'completed'
        session.save()
    
    messages.success(request, "Session settled successfully!")
    return redirect('core:session_detail', session_id=session_id)


@login_required
@require_http_methods(["POST"])
def add_winnings_to_wallet(request, session_id):
    """Add winnings to wallet"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    if session.better_a != request.user and session.better_b != request.user:
        messages.error(request, "You are not authorized to perform this action")
        return redirect('core:session_detail', session_id=session_id)
    
    if session.status != 'completed':
        messages.error(request, "Session is not completed yet")
        return redirect('core:session_detail', session_id=session_id)
    
    # Calculate user's winnings (difference amount if winner)
    better_a_total_runs = sum(bet.runs_scored for bet in Bet.objects.filter(session=session, better=session.better_a) if bet.runs_scored is not None)
    better_b_total_runs = sum(bet.runs_scored for bet in Bet.objects.filter(session=session, better=session.better_b) if bet.runs_scored is not None)
    
    better_a_total_value = Decimal(str(better_a_total_runs)) * session.fixed_bet_amount
    better_b_total_value = Decimal(str(better_b_total_runs)) * session.fixed_bet_amount
    difference = abs(better_a_total_value - better_b_total_value)
    
    # Determine if user is winner
    is_winner = False
    if request.user == session.better_a and better_a_total_value > better_b_total_value:
        is_winner = True
    elif request.user == session.better_b and better_b_total_value > better_a_total_value:
        is_winner = True
    
    if not is_winner or difference <= 0:
        messages.error(request, "You have no winnings to add to wallet")
        return redirect('core:session_detail', session_id=session_id)
    
    winnings = difference
    
    try:
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        with db_transaction.atomic():
            wallet.deposit(winnings)
            Transaction.objects.create(
                user=request.user,
                transaction_type='bet_won',
                amount=winnings,
                balance_after=wallet.balance,
                description=f'Winnings from betting session #{session.id}'
            )
        
        messages.success(request, f'Successfully added ₹{winnings} to your wallet!')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('core:session_detail', session_id=session_id)


@login_required
@require_http_methods(["POST"])
def withdraw_winnings(request, session_id):
    """Withdraw winnings (transfer to external account)"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    if session.better_a != request.user and session.better_b != request.user:
        messages.error(request, "You are not authorized to perform this action")
        return redirect('core:session_detail', session_id=session_id)
    
    if session.status != 'completed':
        messages.error(request, "Session is not completed yet")
        return redirect('core:session_detail', session_id=session_id)
    
    # Calculate user's winnings (difference amount if winner)
    better_a_total_runs = sum(bet.runs_scored for bet in Bet.objects.filter(session=session, better=session.better_a) if bet.runs_scored is not None)
    better_b_total_runs = sum(bet.runs_scored for bet in Bet.objects.filter(session=session, better=session.better_b) if bet.runs_scored is not None)
    
    better_a_total_value = Decimal(str(better_a_total_runs)) * session.fixed_bet_amount
    better_b_total_value = Decimal(str(better_b_total_runs)) * session.fixed_bet_amount
    difference = abs(better_a_total_value - better_b_total_value)
    
    # Determine if user is winner
    is_winner = False
    if request.user == session.better_a and better_a_total_value > better_b_total_value:
        is_winner = True
    elif request.user == session.better_b and better_b_total_value > better_a_total_value:
        is_winner = True
    
    if not is_winner or difference <= 0:
        messages.error(request, "You have no winnings to withdraw")
        return redirect('core:session_detail', session_id=session_id)
    
    winnings = difference
    
    # For now, just show a message (withdrawal functionality would need payment gateway integration)
    messages.info(request, f'Withdrawal request for ₹{winnings} has been submitted. This feature requires payment gateway integration.')
    
    return redirect('core:session_detail', session_id=session_id)


@login_required
def check_session_updates(request, session_id):
    """API endpoint to check for session state changes (for real-time updates)"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    # Check if user is part of this session
    if session.better_a != request.user and session.better_b != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Get last update timestamp from request
    last_update = request.GET.get('last_update')
    
    # Get current session state
    better_a_picks = PickedPlayer.objects.filter(session=session, better=session.better_a).select_related('player', 'player__team')
    better_b_picks = PickedPlayer.objects.filter(session=session, better=session.better_b).select_related('player', 'player__team')
    
    # Count picks per team for each better
    better_a_team_a_count = better_a_picks.filter(player__team=session.match.team_a).count()
    better_a_team_b_count = better_a_picks.filter(player__team=session.match.team_b).count()
    better_b_team_a_count = better_b_picks.filter(player__team=session.match.team_a).count()
    better_b_team_b_count = better_b_picks.filter(player__team=session.match.team_b).count()
    
    # Get recently picked players (in last 30 seconds) for notifications
    from datetime import timedelta
    recent_picks = PickedPlayer.objects.filter(
        session=session,
        picked_at__gte=timezone.now() - timedelta(seconds=30)
    ).select_related('player', 'better').order_by('-picked_at')
    
    # Check if session was updated since last check
    session_updated = True
    if last_update:
        try:
            from django.utils.dateparse import parse_datetime
            last_update_dt = parse_datetime(last_update)
            if last_update_dt and session.updated_at <= last_update_dt:
                session_updated = False
        except:
            pass
    
    # Build response with full pick lists
    response_data = {
        'session_id': session.id,
        'status': session.status,
        'current_turn': session.current_turn.username if session.current_turn else None,
        'current_turn_id': session.current_turn.id if session.current_turn else None,
        'is_my_turn': session.current_turn == request.user if session.current_turn else False,
        'updated_at': session.updated_at.isoformat(),
        'picks_completed': session.picks_completed,
        'better_a_picks_count': better_a_picks.count(),
        'better_b_picks_count': better_b_picks.count(),
        'better_a_team_a_count': better_a_team_a_count,
        'better_a_team_b_count': better_a_team_b_count,
        'better_b_team_a_count': better_b_team_a_count,
        'better_b_team_b_count': better_b_team_b_count,
        'better_a_username': session.better_a.username,
        'better_b_username': session.better_b.username,
        'session_updated': session_updated,
        'better_a_picks': [
            {
                'player_id': pick.player.id,
                'player_name': pick.player.name,
                'team_name': pick.player.team.name
            }
            for pick in better_a_picks
        ],
        'better_b_picks': [
            {
                'player_id': pick.player.id,
                'player_name': pick.player.name,
                'team_name': pick.player.team.name
            }
            for pick in better_b_picks
        ],
        'recent_picks': [
            {
                'player_id': pick.player.id,
                'player_name': pick.player.name,
                'better_username': pick.better.username,
                'picked_at': pick.picked_at.isoformat(),
                'is_opponent': pick.better != request.user
            }
            for pick in recent_picks[:5]  # Last 5 picks
        ]
    }
    
    return JsonResponse(response_data)


@login_required
def search_users(request):
    """Search users by username for invite dropdown"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        query = request.GET.get('q', '').strip()
        logger.info(f"Search users called with query: '{query}' by user: {request.user.username}")
        
        if not query or len(query) < 2:
            logger.info("Query too short, returning empty list")
            return JsonResponse({'users': []})
        
        # Search users by username (case-insensitive)
        users = User.objects.filter(
            username__icontains=query
        ).exclude(
            id=request.user.id  # Exclude current user
        ).values('id', 'username')[:20]  # Limit to 20 results
        
        users_list = list(users)
        logger.info(f"Found {len(users_list)} users matching '{query}'")
        
        return JsonResponse({
            'users': users_list
        })
    except Exception as e:
        logger.error(f"Error in search_users: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'users': [], 'error': str(e)}, status=500)


@login_required
def wallet_info_api(request, info_type):
    """API endpoint to get wallet information (exposure, credit, profit-loss, max-win)"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    if info_type == 'credit':
        # Current wallet balance
        return JsonResponse({'value': str(wallet.balance)})
    
    elif info_type == 'exposure':
        # Calculate exposure (liability in ongoing sessions)
        sessions = BettingSession.objects.filter(
            Q(better_a=request.user) | Q(better_b=request.user),
            status__in=['picking', 'betting', 'live']
        ).exclude(status='cancelled')
        
        exposure = sessions.aggregate(total=Sum('fixed_bet_amount'))['total'] or Decimal('0.00')
        return JsonResponse({'value': str(exposure)})
    
    elif info_type == 'profit-loss':
        # Calculate total profit/loss
        sessions = BettingSession.objects.filter(
            Q(better_a=request.user) | Q(better_b=request.user)
        ).exclude(status='cancelled').select_related('match', 'match__team_a', 'match__team_b')
        
        total_profit_loss = Decimal('0.00')
        for session in sessions:
            is_better_a = session.better_a == request.user
            
            if session.status == 'completed':
                if is_better_a:
                    winnings = session.better_a_total_winnings
                else:
                    winnings = session.better_b_total_winnings
                profit_loss = winnings - session.fixed_bet_amount
            else:
                # For ongoing sessions, subtract the bet amount as potential loss
                profit_loss = -session.fixed_bet_amount
            
            total_profit_loss += profit_loss
        
        return JsonResponse({'value': str(total_profit_loss)})
    
    elif info_type == 'max-win':
        # Get max win limit from profile
        profile = getattr(request.user, 'profile', None)
        max_win = Decimal('0.00')
        if profile and profile.max_win_limit:
            max_win = profile.max_win_limit
        
        return JsonResponse({'value': str(max_win)})
    
    else:
        return JsonResponse({'error': 'Invalid info type'}, status=400)


@login_required
@require_http_methods(["GET", "POST"])
def send_invite(request, session_id):
    """Send an invite to join a betting session"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    # Only session creator can send invites
    if session.better_a != request.user:
        messages.error(request, "Only the session creator can send invites")
        return redirect('core:session_detail', session_id=session_id)
    
    # Can't invite if session already has both players
    if session.better_b != session.better_a:
        messages.error(request, "Session already has both players")
        return redirect('core:session_detail', session_id=session_id)
    
    if request.method == 'POST':
        invite_type = request.POST.get('invite_type', 'username')  # username or link
        message = request.POST.get('message', '').strip()
        
        if invite_type == 'username':
            username = request.POST.get('username', '').strip()
            if not username:
                messages.error(request, "Please select a username from the dropdown")
                return redirect('core:send_invite', session_id=session_id)
            
            try:
                invitee = User.objects.get(username=username)
                if invitee == request.user:
                    messages.error(request, "You cannot invite yourself")
                    return redirect('core:send_invite', session_id=session_id)
                
                # Check if invite already exists
                existing = SessionInvite.objects.filter(
                    session=session,
                    invitee=invitee,
                    status='pending'
                ).first()
                
                if existing and not existing.is_expired():
                    messages.info(request, f"An active invite already exists for {username}")
                    return redirect('core:session_detail', session_id=session_id)
                
                invite = SessionInvite.objects.create(
                    session=session,
                    inviter=request.user,
                    invitee=invitee,
                    invitee_username=username,
                    message=message
                )
                messages.success(request, f"Invite sent to {username}!")
                
            except User.DoesNotExist:
                messages.error(request, f"User '{username}' not found")
                return redirect('core:send_invite', session_id=session_id)
        
        elif invite_type == 'link':
            # Generate shareable link
            invite = SessionInvite.objects.create(
                session=session,
                inviter=request.user,
                message=message
            )
            invite_link = request.build_absolute_uri(
                f"/session/{session_id}/invite/{invite.invite_code}/"
            )
            messages.success(request, f"Invite link created! Share this link: {invite_link}")
        
        return redirect('core:session_detail', session_id=session_id)
    
    # GET request - show invite form
    pending_invites = SessionInvite.objects.filter(
        session=session,
        status='pending'
    ).exclude(expires_at__lt=timezone.now())
    
    context = {
        'session': session,
        'pending_invites': pending_invites,
    }
    return render(request, 'core/send_invite.html', context)


@login_required
def accept_invite(request, session_id, invite_code):
    """Accept an invite to join a betting session"""
    session = get_object_or_404(BettingSession, id=session_id)
    invite = get_object_or_404(SessionInvite, invite_code=invite_code, session=session)
    
    # Check if invite is valid
    if invite.is_expired():
        messages.error(request, "This invite has expired")
        invite.status = 'expired'
        invite.save()
        return redirect('core:home')
    
    if invite.status != 'pending':
        messages.error(request, f"This invite has already been {invite.status}")
        return redirect('core:home')
    
    # If invite has specific invitee, check it matches
    if invite.invitee and invite.invitee != request.user:
        messages.error(request, "This invite is not for you")
        return redirect('core:home')
    
    # Check if session is still available
    if session.better_b != session.better_a:
        messages.error(request, "This session is already full")
        invite.status = 'expired'
        invite.save()
        return redirect('core:home')
    
    # Accept the invite
    if invite.accept(request.user):
        messages.success(request, f"You've joined {invite.inviter.username}'s betting session!")
        return redirect('core:session_detail', session_id=session_id)
    else:
        messages.error(request, "Unable to accept invite. Session may be full or expired.")
        return redirect('core:home')


@login_required
def my_invites(request):
    """View all invites (sent and received)"""
    # Invites sent by user
    sent_invites = SessionInvite.objects.filter(inviter=request.user).select_related('session', 'invitee', 'session__match')
    
    # Invites received by user
    received_invites = SessionInvite.objects.filter(
        invitee=request.user,
        status='pending'
    ).select_related('session', 'inviter', 'session__match').exclude(expires_at__lt=timezone.now())
    
    # Invites by email (if user's email matches)
    email_invites = SessionInvite.objects.filter(
        invitee_email=request.user.email,
        status='pending',
        invitee__isnull=True
    ).select_related('session', 'inviter', 'session__match').exclude(expires_at__lt=timezone.now())
    
    context = {
        'sent_invites': sent_invites,
        'received_invites': received_invites,
        'email_invites': email_invites,
    }
    return render(request, 'core/my_invites.html', context)


@login_required
@require_http_methods(["POST"])
def decline_invite(request, invite_id):
    """Decline an invite"""
    invite = get_object_or_404(SessionInvite, id=invite_id)
    
    # Only invitee can decline
    if invite.invitee and invite.invitee != request.user:
        messages.error(request, "You cannot decline this invite")
        return redirect('core:my_invites')
    
    # Also allow declining by email match
    if invite.invitee_email and invite.invitee_email != request.user.email:
        messages.error(request, "You cannot decline this invite")
        return redirect('core:my_invites')
    
    if invite.decline(request.user):
        messages.success(request, "Invite declined")
    else:
        messages.error(request, "Unable to decline invite")
    
    return redirect('core:my_invites')


# ==================== DISTRIBUTOR/DEALER SYSTEM VIEWS ====================

def is_master_dl(user):
    """Check if user is Master DL (Superuser)"""
    return user.is_superuser or user.is_staff

@user_passes_test(is_master_dl)
def master_dl_dashboard(request):
    """Master DL dashboard"""
    from accounts.models import UserProfile
    from django.db.models import Prefetch
    
    # Get all DL users with their wallets
    # Use select_related for OneToOne relationships
    dl_users = User.objects.filter(
        profile__user_type='dl'
    ).select_related('profile', 'dl_wallet').order_by('-id')
    
    # Ensure all DL users have wallets (create if missing)
    for dl_user in dl_users:
        if not hasattr(dl_user, 'dl_wallet'):
            DLWallet.objects.create(dl_user=dl_user, balance=Decimal('0.00'))
    
    # Refresh the queryset to include newly created wallets
    dl_users = User.objects.filter(
        profile__user_type='dl'
    ).select_related('profile', 'dl_wallet').order_by('-id')
    
    # Statistics
    total_dl_users = dl_users.count()
    total_dl_balance = DLWallet.objects.aggregate(
        total=Sum('balance')
    )['total'] or Decimal('0.00')
    total_credited = DLWallet.objects.aggregate(
        total=Sum('total_credited')
    )['total'] or Decimal('0.00')
    
    context = {
        'total_dl_users': total_dl_users,
        'total_dl_balance': total_dl_balance,
        'total_credited': total_credited,
        'dl_users': dl_users,
    }
    return render(request, 'core/master_dl/dashboard.html', context)

@user_passes_test(is_master_dl)
@require_http_methods(["POST"])
def master_dl_add_points(request, dl_user_id):
    """Master DL adds points to DL user wallet (inline)"""
    dl_user = get_object_or_404(User, id=dl_user_id)
    
    amount = Decimal(request.POST.get('amount', '0.00'))
    description = request.POST.get('description', f'Credit by Master DL')
    
    if amount <= 0:
        error_msg = "Amount must be greater than 0"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('core:master_dl_dashboard')
    
    try:
        dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=dl_user)
        dl_wallet.credit(amount, description)
        
        success_msg = f'₹{amount} added to {dl_user.username}\'s wallet'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': success_msg})
        messages.success(request, success_msg)
        return redirect('core:master_dl_dashboard')
    except Exception as e:
        error_msg = f"Error adding points: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
        messages.error(request, error_msg)
        return redirect('core:master_dl_dashboard')

@user_passes_test(is_master_dl)
@require_http_methods(["POST"])
def master_dl_subtract_points(request, dl_user_id):
    """Master DL subtracts points from DL user wallet (inline)"""
    from django.http import JsonResponse
    
    dl_user = get_object_or_404(User, id=dl_user_id)
    
    amount = Decimal(request.POST.get('amount', '0.00'))
    description = request.POST.get('description', f'Withdrawal by Master DL')
    
    if amount <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Amount must be greater than 0'}, status=400)
        messages.error(request, "Amount must be greater than 0")
        return redirect('core:master_dl_dashboard')
    
    try:
        dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=dl_user)
        
        # Check balance
        if dl_wallet.balance < amount:
            error_msg = f"Insufficient balance. Current balance: ₹{dl_wallet.balance}"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('core:master_dl_dashboard')
        
        # Withdraw
        if dl_wallet.withdraw(amount, description):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f'₹{amount} subtracted from {dl_user.username}\'s wallet'})
            messages.success(request, f'₹{amount} subtracted from {dl_user.username}\'s wallet')
        else:
            error_msg = "Failed to subtract amount"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=500)
            messages.error(request, error_msg)
        
        return redirect('core:master_dl_dashboard')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        messages.error(request, f"Error: {str(e)}")
        return redirect('core:master_dl_dashboard')

@user_passes_test(is_master_dl)
def master_dl_statement(request):
    """Master DL statement view - all transactions"""
    # Get all DL transactions
    transactions = DLTransaction.objects.all().select_related('dl_user').order_by('-created_at')[:100]
    
    # Statistics
    total_credits = DLTransaction.objects.filter(transaction_type='credit').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    total_debits = DLTransaction.objects.filter(transaction_type='debit').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    context = {
        'transactions': transactions,
        'total_credits': total_credits,
        'total_debits': total_debits,
    }
    return render(request, 'core/master_dl/statement.html', context)

@user_passes_test(is_master_dl)
def master_dl_user_statement(request, dl_user_id):
    """Individual DL user statement"""
    dl_user = get_object_or_404(User, id=dl_user_id)
    
    # Get all transactions for this DL user
    transactions = DLTransaction.objects.filter(
        dl_user=dl_user
    ).order_by('-created_at')
    
    # Statistics
    total_credits = DLTransaction.objects.filter(
        dl_user=dl_user,
        transaction_type='credit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_debits = DLTransaction.objects.filter(
        dl_user=dl_user,
        transaction_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=dl_user)
    
    context = {
        'dl_user': dl_user,
        'transactions': transactions,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'current_balance': dl_wallet.balance,
    }
    return render(request, 'core/master_dl/user_statement.html', context)

@user_passes_test(is_master_dl)
def create_dl_user(request):
    """Create a new DL user"""
    from accounts.models import UserProfile
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        initial_balance = Decimal(request.POST.get('initial_balance', '0'))
        
        # Validate input
        if not username or not password:
            messages.error(request, "Username and password are required")
            return render(request, 'core/master_dl/create_dl_user.html')
        
        try:
            # Create user (email is optional)
            user = User.objects.create_user(
                username=username,
                email=email if email else f"{username}@dl.local",
                password=password
            )
            
            # Get or create profile - the signal may have already created it
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Always update to ensure it's set as DL user
            profile.user_type = 'dl'
            profile.master_dl = request.user
            profile.save()
            
            # Create DL wallet
            dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=user)
            
            # Credit initial balance if provided
            if initial_balance > 0:
                dl_wallet.credit(initial_balance, f'Initial credit from Master DL')
            
            messages.success(request, f'DL user {username} created successfully')
            return redirect('core:master_dl_dashboard')
            
        except IntegrityError as e:
            if 'username' in str(e).lower():
                messages.error(request, f"Username '{username}' already exists")
            elif 'email' in str(e).lower():
                messages.error(request, f"Email '{email}' already exists")
            else:
                messages.error(request, f"Error creating user: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error creating DL user: {str(e)}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating DL user: {str(e)}", exc_info=True)
    
    return render(request, 'core/master_dl/create_dl_user.html')

@user_passes_test(is_master_dl)
def credit_dl_wallet(request, dl_user_id):
    """Credit amount to DL user's wallet"""
    dl_user = get_object_or_404(User, id=dl_user_id)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        description = request.POST.get('description', '')
        
        if amount <= 0:
            messages.error(request, "Amount must be greater than 0")
            return redirect('core:credit_dl_wallet', dl_user_id=dl_user_id)
        
        dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=dl_user)
        dl_wallet.credit(amount, description)
        
        messages.success(request, f'₹{amount} credited to {dl_user.username}')
        return redirect('core:master_dl_dashboard')
    
    dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=dl_user)
    context = {'dl_user': dl_user, 'dl_wallet': dl_wallet}
    return render(request, 'core/master_dl/credit_wallet.html', context)

@user_passes_test(is_master_dl)
def withdraw_dl_wallet(request, dl_user_id):
    """Withdraw amount from DL user's wallet"""
    dl_user = get_object_or_404(User, id=dl_user_id)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        description = request.POST.get('description', '')
        
        if amount <= 0:
            messages.error(request, "Amount must be greater than 0")
            return redirect('core:withdraw_dl_wallet', dl_user_id=dl_user_id)
        
        dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=dl_user)
        
        # Check balance
        if dl_wallet.balance < amount:
            messages.error(request, f"Insufficient balance. Current balance: ₹{dl_wallet.balance}")
            return redirect('core:withdraw_dl_wallet', dl_user_id=dl_user_id)
        
        # Withdraw
        if dl_wallet.withdraw(amount, description):
            messages.success(request, f'₹{amount} withdrawn from {dl_user.username}')
        else:
            messages.error(request, "Failed to withdraw amount")
        
        return redirect('core:master_dl_dashboard')
    
    dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=dl_user)
    context = {'dl_user': dl_user, 'dl_wallet': dl_wallet}
    return render(request, 'core/master_dl/withdraw_wallet.html', context)

@user_passes_test(is_master_dl)
def reset_dl_password(request, dl_user_id):
    """Reset password for DL user"""
    from django.contrib.auth.hashers import make_password
    
    dl_user = get_object_or_404(User, id=dl_user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not new_password or len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long")
            return redirect('core:reset_dl_password', dl_user_id=dl_user_id)
        
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('core:reset_dl_password', dl_user_id=dl_user_id)
        
        # Set new password
        dl_user.set_password(new_password)
        dl_user.save()
        
        messages.success(request, f'Password reset successfully for {dl_user.username}')
        return redirect('core:master_dl_dashboard')
    
    context = {'dl_user': dl_user}
    return render(request, 'core/master_dl/reset_password.html', context)

@login_required
def dl_dashboard(request):
    """DL user dashboard with client list and statistics"""
    from accounts.models import UserProfile
    from django.db.models import Q, Sum, F
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    # Get DL wallet
    dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=request.user)
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '').strip()
    active_filter = request.GET.get('active', '')
    
    # Base queryset for end users
    end_users_qs = User.objects.filter(profile__dl_user=request.user).select_related('profile', 'wallet')
    
    # Apply search filter
    if search_query:
        end_users_qs = end_users_qs.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Apply active filter
    if active_filter == 'active':
        end_users_qs = end_users_qs.filter(profile__is_active=True)
    elif active_filter == 'inactive':
        end_users_qs = end_users_qs.filter(profile__is_active=False)
    
    # Ensure all end users have wallets
    for end_user in end_users_qs:
        if not hasattr(end_user, 'wallet'):
            Wallet.objects.get_or_create(user=end_user)
    
    # Refresh the queryset
    end_users = User.objects.filter(id__in=end_users_qs.values_list('id', flat=True)).select_related('profile', 'wallet')
    
    # Calculate statistics for each client
    client_stats = []
    for end_user in end_users:
        # Get all betting sessions involving this client
        sessions = BettingSession.objects.filter(
            Q(better_a=end_user) | Q(better_b=end_user)
        ).exclude(status='cancelled')
        
        # Calculate Profit/Loss
        profit_loss = Decimal('0.00')
        for session in sessions:
            if session.status == 'completed':
                if session.better_a == end_user:
                    profit_loss += (session.better_a_total_winnings - session.fixed_bet_amount)
                elif session.better_b == end_user:
                    profit_loss += (session.better_b_total_winnings - session.fixed_bet_amount)
            elif session.status in ['picking', 'betting', 'live']:
                # For ongoing sessions, subtract the bet amount as potential loss
                profit_loss -= session.fixed_bet_amount
        
        # Calculate Liability (sum of fixed_bet_amount for ongoing sessions)
        liability = sessions.filter(status__in=['picking', 'betting', 'live']).aggregate(
            total=Sum('fixed_bet_amount')
        )['total'] or Decimal('0.00')
        
        # Get client profile data
        profile = end_user.profile if hasattr(end_user, 'profile') else None
        wallet = end_user.wallet if hasattr(end_user, 'wallet') else None
        
        client_stats.append({
            'user': end_user,
            'profile': profile,
            'wallet': wallet,
            'profit_loss': profit_loss,
            'liability': liability,
            'balance': wallet.balance if wallet else Decimal('0.00'),
            'max_win_limit': profile.max_win_limit if profile and profile.max_win_limit else Decimal('0.00'),
            'match_commission': profile.match_commission if profile and profile.match_commission else Decimal('0.00'),
            'session_commission': profile.session_commission if profile and profile.session_commission else Decimal('0.00'),
            'is_active': profile.is_active if profile else True,
        })
    
    # Get pending deposit requests
    pending_requests = DepositRequest.objects.filter(
        dl_user=request.user,
        status='pending'
    ).order_by('-requested_at')
    
    # Statistics
    total_end_users = User.objects.filter(profile__dl_user=request.user).count()
    total_distributed = dl_wallet.total_distributed
    
    context = {
        'dl_wallet': dl_wallet,
        'client_stats': client_stats,
        'pending_requests': pending_requests,
        'total_end_users': total_end_users,
        'total_distributed': total_distributed,
        'search_query': search_query,
        'active_filter': active_filter,
    }
    return render(request, 'core/dl/dashboard.html', context)

@login_required
def approve_deposit_request(request, request_id):
    """Approve a deposit request"""
    deposit_request = get_object_or_404(DepositRequest, id=request_id)
    
    # Check if user is the DL for this request
    if deposit_request.dl_user != request.user:
        messages.error(request, "Unauthorized access")
        return redirect('core:dl_dashboard')
    
    success, message = deposit_request.approve(request.user)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect('core:dl_dashboard')

@login_required
def reject_deposit_request(request, request_id):
    """Reject a deposit request"""
    deposit_request = get_object_or_404(DepositRequest, id=request_id)
    
    if deposit_request.dl_user != request.user:
        messages.error(request, "Unauthorized access")
        return redirect('core:dl_dashboard')
    
    if request.method == 'POST':
        remarks = request.POST.get('remarks', '')
        deposit_request.reject(request.user, remarks)
        messages.success(request, "Deposit request rejected")
        return redirect('core:dl_dashboard')
    
    context = {'deposit_request': deposit_request}
    return render(request, 'core/dl/reject_request.html', context)

@login_required
def request_deposit(request):
    """End user requests deposit from DL"""
    from accounts.models import UserProfile
    
    # Check if user has assigned DL
    if not hasattr(request.user, 'profile') or not request.user.profile.dl_user:
        messages.error(request, "No DL user assigned. Please contact support.")
        return redirect('core:wallet')
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        dl_user = request.user.profile.dl_user
        
        # Create deposit request
        deposit_request = DepositRequest.objects.create(
            end_user=request.user,
            dl_user=dl_user,
            amount=amount,
            status='pending'
        )
        
        messages.success(request, f'Deposit request of ₹{amount} sent to your DL user')
        return redirect('core:wallet')
    
    dl_user = request.user.profile.dl_user
    context = {'dl_user': dl_user}
    return render(request, 'core/deposit_request.html', context)

@login_required
def my_deposit_requests(request):
    """View user's deposit requests"""
    requests = DepositRequest.objects.filter(
        end_user=request.user
    ).order_by('-requested_at')
    
    context = {'requests': requests}
    return render(request, 'core/my_deposit_requests.html', context)

@login_required
def dl_transactions(request):
    """View DL user's transaction history"""
    from accounts.models import UserProfile
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    # Get DL transactions
    transactions = DLTransaction.objects.filter(
        dl_user=request.user
    ).order_by('-created_at')[:50]
    
    context = {
        'transactions': transactions,
    }
    return render(request, 'core/dl/transactions.html', context)

@login_required
def dl_credit_end_user(request, end_user_id):
    """DL user credits points directly to end user"""
    from accounts.models import UserProfile
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    end_user = get_object_or_404(User, id=end_user_id)
    
    # Check if end user is assigned to this DL
    if not hasattr(end_user, 'profile') or end_user.profile.dl_user != request.user:
        messages.error(request, "This user is not assigned to you.")
        return redirect('core:dl_dashboard')
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        description = request.POST.get('description', '')
        
        if amount <= 0:
            messages.error(request, "Amount must be greater than 0")
            return redirect('core:dl_credit_end_user', end_user_id=end_user_id)
        
        # Get DL wallet
        dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=request.user)
        
        # Check DL wallet balance
        if dl_wallet.balance < amount:
            messages.error(request, f"Insufficient balance. Your balance: ₹{dl_wallet.balance}")
            return redirect('core:dl_credit_end_user', end_user_id=end_user_id)
        
        # Debit from DL wallet
        if not dl_wallet.debit(amount, f'Credit to {end_user.username}'):
            messages.error(request, "Failed to debit from DL wallet")
            return redirect('core:dl_credit_end_user', end_user_id=end_user_id)
        
        # Credit to end user wallet
        end_user_wallet, _ = Wallet.objects.get_or_create(user=end_user)
        end_user_wallet.deposit(amount)
        
        # Create transaction record
        Transaction.objects.create(
            user=end_user,
            transaction_type='deposit',
            amount=amount,
            balance_after=end_user_wallet.balance,
            description=description or f'Credited by DL: {request.user.username}'
        )
        
        messages.success(request, f'₹{amount} credited to {end_user.username} successfully')
        return redirect('core:dl_dashboard')
    
    # Get DL wallet for balance display
    dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=request.user)
    
    context = {
        'end_user': end_user,
        'dl_wallet': dl_wallet,
    }
    return render(request, 'core/dl/credit_end_user.html', context)

@login_required
def dl_withdraw_end_user(request, end_user_id):
    """DL user withdraws points from end user"""
    from accounts.models import UserProfile
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    end_user = get_object_or_404(User, id=end_user_id)
    
    # Check if end user is assigned to this DL
    if not hasattr(end_user, 'profile') or end_user.profile.dl_user != request.user:
        messages.error(request, "This user is not assigned to you.")
        return redirect('core:dl_dashboard')
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        description = request.POST.get('description', '')
        
        if amount <= 0:
            messages.error(request, "Amount must be greater than 0")
            return redirect('core:dl_dashboard')
        
        # Get end user wallet
        end_user_wallet, _ = Wallet.objects.get_or_create(user=end_user)
        
        # Check end user wallet balance
        if end_user_wallet.balance < amount:
            messages.error(request, f"Insufficient balance. User balance: ₹{end_user_wallet.balance}")
            return redirect('core:dl_dashboard')
        
        # Withdraw from end user wallet
        end_user_wallet.withdraw(amount)
        
        # Credit to DL wallet
        dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=request.user)
        dl_wallet.credit(amount, f'Withdrawal from {end_user.username}')
        
        # Create transaction record
        Transaction.objects.create(
            user=end_user,
            transaction_type='withdrawal',
            amount=amount,
            balance_after=end_user_wallet.balance,
            description=description or f'Withdrawn by DL: {request.user.username}'
        )
        
        messages.success(request, f'₹{amount} withdrawn from {end_user.username} successfully')
        return redirect('core:dl_dashboard')
    
    # For GET requests, redirect to dashboard
    return redirect('core:dl_dashboard')

@login_required
def dl_user_statement(request, end_user_id):
    """DL user views statement for an end user with enhanced filters and calculations"""
    from accounts.models import UserProfile
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    end_user = get_object_or_404(User, id=end_user_id)
    
    # Check if end user is assigned to this DL
    if not hasattr(end_user, 'profile') or end_user.profile.dl_user != request.user:
        messages.error(request, "This user is not assigned to you.")
        return redirect('core:dl_dashboard')
    
    # Get filter parameter
    filter_type = request.GET.get('filter', 'all')
    
    # Get user profile for commission rates
    profile = end_user.profile if hasattr(end_user, 'profile') else None
    match_commission = profile.match_commission if profile and profile.match_commission else Decimal('0.00')
    session_commission = profile.session_commission if profile and profile.session_commission else Decimal('0.00')
    
    # Get all transactions
    all_transactions = Transaction.objects.filter(user=end_user).order_by('-created_at')
    
    # Get all betting sessions for this user
    sessions = BettingSession.objects.filter(
        Q(better_a=end_user) | Q(better_b=end_user)
    ).exclude(status='cancelled').select_related('match', 'match__team_a', 'match__team_b').order_by('-created_at')
    
    # Build statement entries combining transactions and session results
    statement_entries = []
    
    # Add transaction entries
    for trans in all_transactions:
        entry_type = 'cash'
        if trans.transaction_type in ['deposit', 'withdrawal']:
            entry_type = 'cash'
        elif trans.transaction_type in ['bet_placed', 'bet_won', 'bet_lost']:
            entry_type = 'session'
        
        statement_entries.append({
            'date': trans.created_at,
            'type': 'Cash Entry' if entry_type == 'cash' else 'Session',
            'description': trans.description or trans.get_transaction_type_display(),
            'credit': trans.amount if trans.transaction_type in ['deposit', 'bet_won', 'refund'] else Decimal('0.00'),
            'debit': trans.amount if trans.transaction_type in ['withdrawal', 'bet_placed', 'bet_lost'] else Decimal('0.00'),
            'balance': trans.balance_after,
            'bets': trans.amount if trans.transaction_type == 'bet_placed' else Decimal('0.00'),
            'entry_type': entry_type,
            'transaction_type': trans.transaction_type,
            'session_id': None,
            'match_name': None,
        })
    
    # Add session entries (profit/loss calculations)
    for session in sessions:
        is_better_a = session.better_a == end_user
        is_better_b = session.better_b == end_user
        
        if session.status == 'completed':
            # Calculate profit/loss for this session
            if is_better_a:
                winnings = session.better_a_total_winnings
                bet_amount = session.fixed_bet_amount
            else:
                winnings = session.better_b_total_winnings
                bet_amount = session.fixed_bet_amount
            
            profit_loss = winnings - bet_amount
            
            # Only add entry if there's actual profit/loss (winnings > 0 or loss)
            if winnings > 0 or profit_loss != Decimal('0.00'):
                match_name = f"{session.match.team_a.name} vs {session.match.team_b.name}"
                
                statement_entries.append({
                    'date': session.updated_at,  # Use settlement date
                    'type': 'Session',
                    'description': f'Session #{session.id} - {match_name}',
                    'credit': winnings if winnings > 0 else Decimal('0.00'),
                    'debit': Decimal('0.00'),
                    'balance': None,  # Will be calculated
                    'bets': bet_amount,
                    'entry_type': 'session',
                    'transaction_type': 'session_result',
                    'session_id': session.id,
                    'match_name': match_name,
                    'profit_loss': profit_loss,
                })
    
    # Sort by date descending
    statement_entries.sort(key=lambda x: x['date'], reverse=True)
    
    # Calculate running balance
    current_balance = Decimal('0.00')
    wallet, _ = Wallet.objects.get_or_create(user=end_user)
    current_balance = wallet.balance
    
    # Calculate balances backwards from current
    for entry in reversed(statement_entries):
        if entry['balance'] is None:
            entry['balance'] = current_balance
        current_balance = entry['balance'] - entry['credit'] + entry['debit']
    
    # Calculate statistics
    cash_entries = [e for e in statement_entries if e['entry_type'] == 'cash']
    session_entries = [e for e in statement_entries if e['entry_type'] == 'session']
    
    # Cash entry totals
    cash_credit = sum(e['credit'] for e in cash_entries)
    cash_debit = sum(e['debit'] for e in cash_entries)
    cash_net = cash_credit - cash_debit
    
    # Session profit/loss
    session_profit_loss = sum(e.get('profit_loss', e['credit'] - e['bets']) for e in session_entries if e.get('profit_loss') is not None or e['credit'] > 0)
    
    # Market profit/loss (same as session for now, as all are session-based)
    market_profit_loss = session_profit_loss
    
    # Calculate commissions
    total_bets = sum(e['bets'] for e in session_entries)
    market_commission = (total_bets * match_commission / 100) if match_commission > 0 else Decimal('0.00')
    session_commission_amount = (total_bets * session_commission / 100) if session_commission > 0 else Decimal('0.00')
    
    # Total profit/loss
    total_profit_loss = cash_net + session_profit_loss - market_commission - session_commission_amount
    
    # Apply filters
    if filter_type == 'cash_and_market':
        statement_entries = [e for e in statement_entries if e['entry_type'] == 'cash' or (e['entry_type'] == 'session' and e.get('profit_loss', 0) != 0)]
    elif filter_type == 'cash_only':
        statement_entries = [e for e in statement_entries if e['entry_type'] == 'cash']
    elif filter_type == 'market_commission':
        # Show only commission entries (we'll add these)
        statement_entries = []
    elif filter_type == 'session_pl':
        statement_entries = [e for e in statement_entries if e['entry_type'] == 'session']
    elif filter_type == 'total_pl':
        # Show all entries
        pass
    elif filter_type == 'market_pl':
        statement_entries = [e for e in statement_entries if e['entry_type'] == 'session']
    # 'all' shows everything
    
    context = {
        'end_user': end_user,
        'statement_entries': statement_entries,
        'current_balance': wallet.balance,
        'cash_credit': cash_credit,
        'cash_debit': cash_debit,
        'cash_net': cash_net,
        'session_profit_loss': session_profit_loss,
        'market_profit_loss': market_profit_loss,
        'market_commission': market_commission,
        'session_commission': session_commission_amount,
        'total_profit_loss': total_profit_loss,
        'total_bets': total_bets,
        'filter_type': filter_type,
    }
    
    # If AJAX request, return only the content area
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'core/dl/user_statement_content.html', context)
    
    return render(request, 'core/dl/user_statement.html', context)

@login_required
def dl_assign_end_user(request):
    """DL user assigns an end user to themselves"""
    from accounts.models import UserProfile
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        
        if not username:
            messages.error(request, "Please enter a username")
            return redirect('core:dl_assign_end_user')
        
        try:
            end_user = User.objects.get(username=username)
            
            # Check if user is already assigned to another DL
            if hasattr(end_user, 'profile') and end_user.profile.dl_user and end_user.profile.dl_user != request.user:
                messages.error(request, f"User {username} is already assigned to another DL user")
                return redirect('core:dl_assign_end_user')
            
            # Assign to this DL
            profile, _ = UserProfile.objects.get_or_create(user=end_user)
            profile.dl_user = request.user
            profile.user_type = 'end_user'  # Ensure it's marked as end user
            profile.save()
            
            messages.success(request, f'User {username} assigned to you successfully')
            return redirect('core:dl_dashboard')
            
        except User.DoesNotExist:
            messages.error(request, f"User '{username}' not found")
            return redirect('core:dl_assign_end_user')
    
    return render(request, 'core/dl/assign_end_user.html')

@login_required
def dl_home(request):
    """DL user home page with match filtering"""
    from accounts.models import UserProfile
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    # Get filter preferences from request - only true if explicitly set to 'true'
    # This allows single checkbox selection
    show_completed = request.GET.get('completed') == 'true'
    show_ongoing = request.GET.get('ongoing') == 'true'
    show_suspended = request.GET.get('suspended') == 'true'
    
    # If no filters are selected on first load, default to showing all
    if not any([show_completed, show_ongoing, show_suspended]) and not request.GET:
        show_completed = True
        show_ongoing = True
        show_suspended = True
    
    # Build match query based on filters using Q objects
    from django.db.models import Q
    status_filters = Q()
    
    if show_completed:
        status_filters |= Q(status='completed')
    if show_ongoing:
        status_filters |= Q(status='live')
    if show_suspended:
        status_filters |= Q(status='abandoned')
    
    # Apply filters - if none selected after user interaction, show nothing
    if not show_completed and not show_ongoing and not show_suspended and request.GET:
        matches = Match.objects.none()  # Empty queryset
    else:
        matches = Match.objects.filter(status_filters).order_by('-match_date')
    
    context = {
        'matches': matches,
        'show_completed': show_completed,
        'show_ongoing': show_ongoing,
        'show_suspended': show_suspended,
    }
    return render(request, 'core/dl/home.html', context)

@login_required
def dl_add_user(request):
    """DL user creates a new end user"""
    from accounts.models import UserProfile
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        initial_balance = Decimal(request.POST.get('initial_balance', '0'))
        max_win_limit = Decimal(request.POST.get('max_win_limit', '0') or '0')
        match_commission = Decimal(request.POST.get('match_commission', '0') or '0')
        session_commission = Decimal(request.POST.get('session_commission', '0') or '0')
        
        # Validate input
        if not username or not password:
            messages.error(request, "Username and password are required")
            return render(request, 'core/dl/add_user.html')
        
        # Validate commission percentages
        if match_commission < 0 or match_commission > 100:
            messages.error(request, "Match commission must be between 0 and 100")
            return render(request, 'core/dl/add_user.html')
        
        if session_commission < 0 or session_commission > 100:
            messages.error(request, "Session commission must be between 0 and 100")
            return render(request, 'core/dl/add_user.html')
        
        try:
            with db_transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    password=password
                )
                
                # Get or create profile
                profile, created = UserProfile.objects.get_or_create(user=user)
                
                # Assign to this DL and set client-specific fields
                profile.user_type = 'end_user'
                profile.dl_user = request.user
                if max_win_limit > 0:
                    profile.max_win_limit = max_win_limit
                if match_commission > 0:
                    profile.match_commission = match_commission
                if session_commission > 0:
                    profile.session_commission = session_commission
                profile.save()
                
                # Create wallet
                wallet, _ = Wallet.objects.get_or_create(user=user)
                
                # Credit initial balance if provided
                if initial_balance > 0:
                    wallet.deposit(initial_balance)
                    Transaction.objects.create(
                        user=user,
                        transaction_type='deposit',
                        amount=initial_balance,
                        balance_after=wallet.balance,
                        description=f'Initial credit from DL {request.user.username}'
                    )
                    
                    # Deduct from DL wallet
                    dl_wallet, _ = DLWallet.objects.get_or_create(dl_user=request.user)
                    if dl_wallet.balance >= initial_balance:
                        dl_wallet.debit(initial_balance, f'Initial credit for {username}')
                    else:
                        messages.warning(request, f'User created but insufficient DL balance to credit initial amount')
                
                messages.success(request, f'Client {username} created successfully')
                return redirect('core:dl_dashboard')
                
        except IntegrityError as e:
            if 'username' in str(e).lower():
                messages.error(request, f"Username '{username}' already exists")
            else:
                messages.error(request, f"Error creating user: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error creating client: {str(e)}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating client: {str(e)}", exc_info=True)
    
    return render(request, 'core/dl/add_user.html')

@login_required
def dl_edit_user(request, end_user_id):
    """DL user edits an end user"""
    from accounts.models import UserProfile
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    end_user = get_object_or_404(User, id=end_user_id)
    
    # Check if end user is assigned to this DL
    if not hasattr(end_user, 'profile') or end_user.profile.dl_user != request.user:
        messages.error(request, "This user is not assigned to you.")
        return redirect('core:dl_dashboard')
    
    profile = end_user.profile if hasattr(end_user, 'profile') else None
    
    if request.method == 'POST':
        password = request.POST.get('password')
        max_win_limit = Decimal(request.POST.get('max_win_limit', '0') or '0')
        match_commission = Decimal(request.POST.get('match_commission', '0') or '0')
        session_commission = Decimal(request.POST.get('session_commission', '0') or '0')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validate commission percentages
        if match_commission < 0 or match_commission > 100:
            messages.error(request, "Match commission must be between 0 and 100")
            return render(request, 'core/dl/edit_user.html', {'end_user': end_user, 'profile': profile})
        
        if session_commission < 0 or session_commission > 100:
            messages.error(request, "Session commission must be between 0 and 100")
            return render(request, 'core/dl/edit_user.html', {'end_user': end_user, 'profile': profile})
        
        try:
            # Get or create profile
            if not profile:
                profile, _ = UserProfile.objects.get_or_create(user=end_user)
                profile.user_type = 'end_user'
                profile.dl_user = request.user
            
            # Update password if provided
            if password:
                end_user.set_password(password)
                end_user.save()
            
            # Update profile fields
            profile.max_win_limit = max_win_limit if max_win_limit > 0 else None
            profile.match_commission = match_commission if match_commission > 0 else None
            profile.session_commission = session_commission if session_commission > 0 else None
            profile.is_active = is_active
            profile.save()
            
            messages.success(request, f'Client {end_user.username} updated successfully')
            return redirect('core:dl_dashboard')
            
        except Exception as e:
            messages.error(request, f"Error updating client: {str(e)}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating client: {str(e)}", exc_info=True)
    
    context = {
        'end_user': end_user,
        'profile': profile,
    }
    return render(request, 'core/dl/edit_user.html', context)

@login_required
def account_statement(request):
    """End user account statement"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate totals
    total_credits = Transaction.objects.filter(
        user=request.user,
        transaction_type__in=['deposit', 'bet_won', 'refund']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_debits = Transaction.objects.filter(
        user=request.user,
        transaction_type__in=['withdrawal', 'bet_placed', 'bet_lost']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'total_credits': total_credits,
        'total_debits': total_debits,
    }
    return render(request, 'core/account_statement.html', context)

@login_required
def profit_loss(request):
    """End user profit & loss report"""
    # Get all betting sessions for this user
    sessions = BettingSession.objects.filter(
        Q(better_a=request.user) | Q(better_b=request.user)
    ).exclude(status='cancelled').select_related('match', 'match__team_a', 'match__team_b').order_by('-created_at')
    
    # Calculate profit/loss for each session
    session_data = []
    total_profit_loss = Decimal('0.00')
    total_bets = Decimal('0.00')
    total_winnings = Decimal('0.00')
    
    for session in sessions:
        is_better_a = session.better_a == request.user
        
        if is_better_a:
            winnings = session.better_a_total_winnings if session.status == 'completed' else Decimal('0.00')
        else:
            winnings = session.better_b_total_winnings if session.status == 'completed' else Decimal('0.00')
        
        bet_amount = session.fixed_bet_amount
        profit_loss = winnings - bet_amount
        
        session_data.append({
            'session': session,
            'match': session.match,
            'bet_amount': bet_amount,
            'winnings': winnings,
            'profit_loss': profit_loss,
            'status': session.status,
        })
        
        total_bets += bet_amount
        total_winnings += winnings
        total_profit_loss += profit_loss
    
    context = {
        'session_data': session_data,
        'total_profit_loss': total_profit_loss,
        'total_bets': total_bets,
        'total_winnings': total_winnings,
    }
    return render(request, 'core/profit_loss.html', context)

@login_required
def bet_history(request):
    """End user bet history"""
    # Get all betting sessions for this user
    sessions = BettingSession.objects.filter(
        Q(better_a=request.user) | Q(better_b=request.user)
    ).select_related('match', 'match__team_a', 'match__team_b', 'better_a', 'better_b').order_by('-created_at')
    
    # Get all bets for this user
    bets = Bet.objects.filter(better=request.user).select_related(
        'session', 'session__match', 'picked_player', 'picked_player__player'
    ).order_by('-session__created_at')
    
    context = {
        'sessions': sessions,
        'bets': bets,
    }
    return render(request, 'core/bet_history.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    """End user change password"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            messages.error(request, "All fields are required")
            return render(request, 'core/change_password.html')
        
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match")
            return render(request, 'core/change_password.html')
        
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long")
            return render(request, 'core/change_password.html')
        
        # Verify old password
        if not request.user.check_password(old_password):
            messages.error(request, "Current password is incorrect")
            return render(request, 'core/change_password.html')
        
        # Set new password
        request.user.set_password(new_password)
        request.user.save()
        
        # Re-authenticate user
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Password changed successfully")
        return redirect('core:home')
    
    return render(request, 'core/change_password.html')

@login_required
def end_user_reports(request):
    """End user reports - own transactions"""
    from accounts.models import UserProfile
    
    # Check if user is end user (not DL or master DL)
    if hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'dl':
            return redirect('core:dl_reports')
        elif request.user.is_superuser or request.user.is_staff:
            return redirect('core:master_dl_reports')
    
    # Get all transactions for this user
    transactions = Transaction.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Filter by transaction type if provided
    transaction_type_filter = request.GET.get('type', '')
    if transaction_type_filter:
        if transaction_type_filter == 'credit':
            transactions = transactions.filter(transaction_type__in=['deposit', 'bet_won', 'refund'])
        elif transaction_type_filter == 'withdraw':
            transactions = transactions.filter(transaction_type__in=['withdrawal', 'bet_placed', 'bet_lost'])
    
    # Filter by date range if provided
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        from django.utils.dateparse import parse_date
        try:
            date_from_obj = parse_date(date_from)
            transactions = transactions.filter(created_at__gte=date_from_obj)
        except:
            pass
    if date_to:
        from django.utils.dateparse import parse_date
        try:
            date_to_obj = parse_date(date_to)
            transactions = transactions.filter(created_at__lte=date_to_obj)
        except:
            pass
    
    context = {
        'transactions': transactions,
        'transaction_type_filter': transaction_type_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'core/reports.html', context)

@login_required
def dl_reports(request):
    """DL user reports - all transactions for their clients"""
    from accounts.models import UserProfile
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    # Get all end users assigned to this DL
    end_users = User.objects.filter(profile__dl_user=request.user)
    
    # Get all transactions for these end users
    transactions = Transaction.objects.filter(
        user__in=end_users
    ).select_related('user').order_by('-created_at')
    
    # Filter by transaction type if provided
    transaction_type_filter = request.GET.get('type', '')
    if transaction_type_filter:
        if transaction_type_filter == 'credit':
            transactions = transactions.filter(transaction_type__in=['deposit', 'bet_won', 'refund'])
        elif transaction_type_filter == 'withdraw':
            transactions = transactions.filter(transaction_type__in=['withdrawal', 'bet_placed', 'bet_lost'])
    
    # Filter by date range if provided
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        from django.utils.dateparse import parse_date
        try:
            date_from_obj = parse_date(date_from)
            transactions = transactions.filter(created_at__gte=date_from_obj)
        except:
            pass
    if date_to:
        from django.utils.dateparse import parse_date
        try:
            date_to_obj = parse_date(date_to)
            transactions = transactions.filter(created_at__lte=date_to_obj)
        except:
            pass
    
    context = {
        'transactions': transactions,
        'transaction_type_filter': transaction_type_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'core/dl/reports.html', context)

@user_passes_test(is_master_dl)
def master_dl_reports(request):
    """Master DL reports - all DL transactions"""
    # Get all DL transactions
    transactions = DLTransaction.objects.all().select_related('dl_user').order_by('-created_at')
    
    # Filter by transaction type if provided
    transaction_type_filter = request.GET.get('type', '')
    if transaction_type_filter:
        if transaction_type_filter == 'credit':
            transactions = transactions.filter(transaction_type='credit')
        elif transaction_type_filter == 'debit':
            transactions = transactions.filter(transaction_type='debit')
    
    # Filter by date range if provided
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        from django.utils.dateparse import parse_date
        try:
            date_from_obj = parse_date(date_from)
            transactions = transactions.filter(created_at__gte=date_from_obj)
        except:
            pass
    if date_to:
        from django.utils.dateparse import parse_date
        try:
            date_to_obj = parse_date(date_to)
            transactions = transactions.filter(created_at__lte=date_to_obj)
        except:
            pass
    
    context = {
        'transactions': transactions,
        'transaction_type_filter': transaction_type_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'core/master_dl/reports.html', context)

@login_required
def dl_match_book(request):
    """DL user match book with betting statistics"""
    from accounts.models import UserProfile
    from django.db.models import Q, Sum, Count, Case, When, DecimalField
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    # Get filter preferences from request - only true if explicitly set to 'true'
    # This allows single checkbox selection
    show_running = request.GET.get('running') == 'true'
    show_suspended = request.GET.get('suspended') == 'true'
    show_completed = request.GET.get('completed') == 'true'
    
    # If no filters are selected on first load, default to showing all
    if not any([show_running, show_suspended, show_completed]) and not request.GET:
        show_running = True
        show_suspended = True
        show_completed = True
    
    # Get end users managed by this DL
    end_users = User.objects.filter(profile__dl_user=request.user)
    end_user_ids = list(end_users.values_list('id', flat=True))
    
    # Build match query based on filters
    from django.db.models import Q
    status_filters = Q()
    
    if show_running:
        status_filters |= Q(status='live')
    if show_suspended:
        status_filters |= Q(status='abandoned')
    if show_completed:
        status_filters |= Q(status='completed')
    
    # Apply filters - if none selected after user interaction, show nothing
    if not show_running and not show_suspended and not show_completed and request.GET:
        matches = Match.objects.none()  # Empty queryset
    else:
        matches = Match.objects.filter(status_filters).order_by('-match_date')
    
    # Calculate statistics for each match
    match_data = []
    for match in matches:
        # Get all betting sessions for this match involving DL's end users
        sessions = BettingSession.objects.filter(
            match=match
        ).filter(
            Q(better_a_id__in=end_user_ids) | Q(better_b_id__in=end_user_ids)
        ).exclude(status='pending').exclude(status='cancelled')
        
        # Match Book: Total bet amount from all sessions
        match_book = sessions.aggregate(
            total=Sum('fixed_bet_amount')
        )['total'] or Decimal('0.00')
        
        # Toss Book: Same as match book (toss is part of the session)
        toss_book = match_book
        
        # Total Book: Match Book + Toss Book (or just match book * 2 if we count separately)
        total_book = match_book * 2  # Since both players bet
        
        # Calculate Client Profit and Loss
        # For each session, calculate net profit/loss for end users
        client_profit_loss = Decimal('0.00')
        for session in sessions:
            # Check if end users are involved
            if session.better_a_id in end_user_ids:
                # End user is better_a
                if session.status == 'completed':
                    # Calculate profit/loss: winnings - bet amount
                    profit = session.better_a_total_winnings - session.fixed_bet_amount
                    client_profit_loss += profit
                else:
                    # For ongoing matches, profit/loss is negative of bet amount (potential loss)
                    client_profit_loss -= session.fixed_bet_amount
            
            if session.better_b_id in end_user_ids:
                # End user is better_b
                if session.status == 'completed':
                    # Calculate profit/loss: winnings - bet amount
                    profit = session.better_b_total_winnings - session.fixed_bet_amount
                    client_profit_loss += profit
                else:
                    # For ongoing matches, profit/loss is negative of bet amount (potential loss)
                    client_profit_loss -= session.fixed_bet_amount
        
        # Open Rate: Average fixed bet amount for sessions on this match
        if sessions.exists():
            avg_bet = sum(s.fixed_bet_amount for s in sessions) / sessions.count()
        else:
            avg_bet = Decimal('0.00')
        
        # Result: Match status or session results
        result = match.get_status_display()
        if match.status == 'completed' and sessions.filter(status='completed').exists():
            completed_sessions = sessions.filter(status='completed')
            if completed_sessions.exists():
                result = f"{completed_sessions.count()} session(s) completed"
        
        match_data.append({
            'match': match,
            'open_rate': avg_bet,
            'result': result,
            'match_book': match_book,
            'toss_book': toss_book,
            'total_book': total_book,
            'client_profit_loss': client_profit_loss,
            'session_count': sessions.count(),
        })
    
    context = {
        'match_data': match_data,
        'show_running': show_running,
        'show_suspended': show_suspended,
        'show_completed': show_completed,
    }
    return render(request, 'core/dl/match_book.html', context)

@login_required
def dl_match_detail(request, match_id):
    """DL user match detail page with tabs for odds, points, bets, and sessions"""
    from accounts.models import UserProfile
    from django.db.models import Q, Sum, Count, F
    
    # Check if user is DL
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dl':
        messages.error(request, "Access denied. You are not a DL user.")
        return redirect('core:home')
    
    match = get_object_or_404(Match, id=match_id)
    
    # Get end users managed by this DL
    end_users = User.objects.filter(profile__dl_user=request.user)
    end_user_ids = list(end_users.values_list('id', flat=True))
    
    # Get all betting sessions for this match involving DL's end users
    sessions = BettingSession.objects.filter(
        match=match
    ).filter(
        Q(better_a_id__in=end_user_ids) | Q(better_b_id__in=end_user_ids)
    ).select_related('better_a', 'better_b', 'match', 'match__team_a', 'match__team_b')
    
    # Match Odds Data (Runner - teams with back/lay odds)
    # For now, we'll use placeholder data structure
    match_odds = [
        {
            'runner': match.team_a.name,
            'back_odds': '1.85',  # Placeholder
            'lay_odds': '1.90',   # Placeholder
        },
        {
            'runner': match.team_b.name,
            'back_odds': '1.95',  # Placeholder
            'lay_odds': '2.00',   # Placeholder
        },
    ]
    
    # Session Details (like "20 overs runs adv" etc)
    session_details = [
        {'label': '20 Overs Runs Adv', 'not': '1.85', 'yes': '1.95'},
        {'label': 'Total Runs Over', 'not': '1.80', 'yes': '2.00'},
        {'label': 'Total Runs Under', 'not': '1.90', 'yes': '1.85'},
    ]
    
    # Total Points Data
    total_points = {
        'team1': Decimal('0.00'),  # Sum of points from sessions for team1
        'team2': Decimal('0.00'),  # Sum of points from sessions for team2
        'drawn': Decimal('0.00'),  # Draw points
    }
    
    # Match Bet Data (aggregated bets from sessions)
    match_bets = []
    bet_counter = 1
    for session in sessions:
        bets = Bet.objects.filter(session=session).select_related('better', 'picked_player', 'picked_player__player', 'picked_player__player__team')
        for bet in bets:
            if bet.better_id in end_user_ids:
                match_bets.append({
                    'sr': bet_counter,
                    'user': bet.better.username,
                    'odds': '1.85',  # Placeholder
                    'stake': session.fixed_bet_amount,
                    'bettype': 'Back',  # Placeholder
                    'team': bet.picked_player.player.team.name,
                    'data': bet.created_at.strftime('%Y-%m-%d %H:%M'),
                })
                bet_counter += 1
    
    # Session Data (similar to match bets but organized by session)
    session_data = []
    session_counter = 1
    for session in sessions:
        bets = Bet.objects.filter(session=session).select_related('better', 'picked_player', 'picked_player__player', 'picked_player__player__team')
        for bet in bets:
            if bet.better_id in end_user_ids:
                session_data.append({
                    'sr': session_counter,
                    'user': bet.better.username,
                    'odds': '1.85',  # Placeholder
                    'stake': session.fixed_bet_amount,
                    'bettype': 'Back',  # Placeholder
                    'team': bet.picked_player.player.team.name,
                    'data': bet.created_at.strftime('%Y-%m-%d %H:%M'),
                })
                session_counter += 1
    
    # Get MatchBet data
    from .models import MatchBet, MatchBetBalance
    existing_match_bets = MatchBet.objects.filter(match=match).select_related('user').order_by('-created_at')
    
    # Get balances for current user
    user_balances = {}
    if request.user.is_authenticated:
        balances = MatchBetBalance.objects.filter(match=match, user=request.user)
        for balance in balances:
            user_balances[balance.selection] = float(balance.balance)
    
    # Organize bets by selection and bet_type for easy lookup (as JSON for JavaScript)
    bets_by_selection = {}
    for bet in existing_match_bets:
        key = f"{bet.selection}_{bet.bet_type}"
        if key not in bets_by_selection:
            bets_by_selection[key] = []
        bets_by_selection[key].append({
            'user': bet.user.username,
            'odds': str(bet.odds),
            'stake': str(bet.stake),
            'created_at': bet.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    # Convert to JSON for JavaScript
    bets_by_selection_json = json.dumps(bets_by_selection)
    user_balances_json = json.dumps(user_balances)
    
    # Update match_bets table to include MatchBet data
    match_bet_counter = len(match_bets) + 1
    for bet in existing_match_bets:
        if bet.user_id in end_user_ids or bet.user == request.user:
            match_bets.append({
                'sr': match_bet_counter,
                'user': bet.user.username,
                'odds': str(bet.odds),
                'stake': bet.stake,
                'bettype': bet.bet_type.upper(),
                'team': bet.selection,
                'data': bet.created_at.strftime('%Y-%m-%d %H:%M'),
            })
            match_bet_counter += 1
    
    context = {
        'match': match,
        'match_odds': match_odds,
        'session_details': session_details,
        'total_points': total_points,
        'match_bets': match_bets,
        'session_data': session_data,
        'sessions_count': sessions.count(),
        'bets_by_selection_json': bets_by_selection_json,
        'user_balances_json': user_balances_json,
        'match_id': match_id,
    }
    return render(request, 'core/dl/match_detail.html', context)


@login_required
@require_http_methods(["POST"])
def dl_place_match_bet(request, match_id):
    """API endpoint to place a match bet from the dropdown"""
    match = get_object_or_404(Match, id=match_id)
    
    # Check if user is DL or end user
    if hasattr(request.user, 'profile') and request.user.profile.user_type == 'dl':
        user = request.user
    else:
        # End users - check if they belong to a DL
        if not hasattr(request.user, 'profile') or not request.user.profile.dl_user:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        user = request.user
    
    try:
        from .models import MatchBet, MatchBetBalance
        from django.db.models import F
        
        data = json.loads(request.body)
        selection = data.get('selection', '').strip()
        bet_type = data.get('bet_type', '').strip().lower()
        odds = Decimal(str(data.get('odds', 0)))
        stake = Decimal(str(data.get('stake', 0)))
        
        # Validation
        if not selection:
            return JsonResponse({'success': False, 'error': 'Selection is required'})
        
        if bet_type not in ['back', 'lay', 'not', 'yes']:
            return JsonResponse({'success': False, 'error': 'Invalid bet type'})
        
        if odds < Decimal('1.01'):
            return JsonResponse({'success': False, 'error': 'Invalid odds'})
        
        if stake < Decimal('0.01'):
            return JsonResponse({'success': False, 'error': 'Invalid stake amount'})
        
        # Check wallet balance (for end users)
        if hasattr(user, 'wallet'):
            if user.wallet.balance < stake:
                return JsonResponse({
                    'success': False,
                    'error': f'Insufficient balance. Required: ₹{stake}, Your balance: ₹{user.wallet.balance}'
                })
            
            # Deduct from wallet
            user.wallet.withdraw(stake)
            Transaction.objects.create(
                user=user,
                transaction_type='bet_placed',
                amount=stake,
                balance_after=user.wallet.balance,
                description=f'Match bet: {bet_type.upper()} {selection} @ {odds}'
            )
        
        # Calculate balance changes
        # For LAY: liability = stake * (odds - 1), selection gets -liability, other gets +stake
        # For BACK: profit = stake * (odds - 1), selection gets +profit, other gets -stake
        
        # Get all teams/selections for this match
        all_selections = [match.team_a.name, match.team_b.name]
        if selection not in all_selections:
            # Session bet, handle differently
            other_selection = None
        else:
            other_selection = all_selections[1] if selection == all_selections[0] else all_selections[0]
        
        # Calculate balance changes
        if bet_type == 'lay':
            liability = stake * (odds - Decimal('1.0'))
            selection_change = -liability
            other_change = stake if other_selection else Decimal('0.00')
        else:  # back, not, yes
            profit = stake * (odds - Decimal('1.0'))
            selection_change = profit
            other_change = -stake if other_selection else Decimal('0.00')
        
        # Create the bet
        match_bet = MatchBet.objects.create(
            match=match,
            user=user,
            selection=selection,
            bet_type=bet_type,
            odds=odds,
            stake=stake
        )
        
        # Update balances - fetch, update, and save (atomic operation)
        # For selection
        balance_obj, created = MatchBetBalance.objects.get_or_create(
            match=match,
            user=user,
            selection=selection,
            defaults={'balance': Decimal('0.00')}
        )
        balance_obj.balance += selection_change
        balance_obj.save()
        selection_balance = balance_obj.balance
        
        # For other selection (if team bet)
        other_balance_obj = None
        other_balance_value = None
        if other_selection:
            other_balance_obj, created = MatchBetBalance.objects.get_or_create(
                match=match,
                user=user,
                selection=other_selection,
                defaults={'balance': Decimal('0.00')}
            )
            other_balance_obj.balance += other_change
            other_balance_obj.save()
            other_balance_value = other_balance_obj.balance
        
        # Prepare response balances
        response_balances = {
            selection: float(selection_balance)
        }
        if other_selection and other_balance_value is not None:
            response_balances[other_selection] = float(other_balance_value)
        
        return JsonResponse({
            'success': True,
            'message': f'Bet placed: {bet_type.upper()} {selection} @ {odds} - ₹{stake}',
            'bet_id': match_bet.id,
            'balances': response_balances
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)