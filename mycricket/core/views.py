from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.db import transaction as db_transaction
from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone
from decimal import Decimal
import json

from .models import (
    Match, Team, Player, Wallet, BettingSession, PickedPlayer, Bet,
    Transaction, PlayerMatchStats
)
from .services import cricket_api


@login_required
def home(request):
    """Home page showing live and upcoming matches"""
    from accounts.models import UserProfile
    
    # Get matches from database (synced from API)
    live_matches = Match.objects.filter(status='live').order_by('-match_date')
    upcoming_matches = Match.objects.filter(status='upcoming').order_by('match_date')
    
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
    
    context = {
        'live_matches': live_matches,
        'upcoming_matches': upcoming_matches,
        'active_sessions': active_sessions,
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
    
    context = {
        'match': match,
        'team_a_players': team_a_players,
        'team_b_players': team_b_players,
        'existing_session': existing_session,
        'available_sessions': available_sessions,
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
    
    # Convert to list and add bet info to picks for template
    better_a_picks = list(better_a_picks_qs)
    better_b_picks = list(better_b_picks_qs)
    for pick in better_a_picks:
        pick.bet = better_a_bets_dict.get(pick.id)
    for pick in better_b_picks:
        pick.bet = better_b_bets_dict.get(pick.id)
    
    # Get available players (not yet picked)
    picked_player_ids = PickedPlayer.objects.filter(session=session).values_list('player_id', flat=True)
    available_players = Player.objects.filter(
        team__in=[session.match.team_a, session.match.team_b]
    ).exclude(id__in=picked_player_ids)
    
    # Group by team
    team_a_available = available_players.filter(team=session.match.team_a)
    team_b_available = available_players.filter(team=session.match.team_b)
    
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
    }
    return render(request, 'core/session_detail.html', context)


@login_required
@require_http_methods(["POST"])
def perform_toss(request, session_id):
    """Perform toss to determine who picks first"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    # Check if user is part of this session
    if session.better_a != request.user and session.better_b != request.user:
        messages.error(request, "You are not authorized to perform toss for this session")
        return redirect('core:session_detail', session_id=session_id)
    
    # Check if both players have joined
    if session.better_b == session.better_a:
        messages.error(request, "Waiting for another player to join")
        return redirect('core:session_detail', session_id=session_id)
    
    # Check if toss already completed
    if session.toss_completed:
        messages.info(request, "Toss already completed")
        return redirect('core:session_detail', session_id=session_id)
    
    # Perform toss
    toss_winner = session.perform_toss()
    
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
    """Place bet on a picked player"""
    session = get_object_or_404(BettingSession, id=session_id)
    
    if session.better_a != request.user and session.better_b != request.user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if session.status != 'betting':
        return JsonResponse({'success': False, 'error': 'Betting phase is not active'})
    
    try:
        data = json.loads(request.body)
        picked_player_id = data.get('picked_player_id')
        amount_per_run = Decimal(str(data.get('amount_per_run', 0)))
        insurance_percentage = Decimal(str(data.get('insurance_percentage', 0)))
        
        if amount_per_run <= 0:
            return JsonResponse({'success': False, 'error': 'Amount must be greater than 0'})
        
        # Validate insurance percentage (0-20%)
        if insurance_percentage < 0 or insurance_percentage > 20:
            return JsonResponse({'success': False, 'error': 'Insurance percentage must be between 0 and 20'})
        
        picked_player = get_object_or_404(PickedPlayer, id=picked_player_id, session=session, better=request.user)
        
        # Check if bet already exists
        if Bet.objects.filter(picked_player=picked_player).exists():
            return JsonResponse({'success': False, 'error': 'Bet already placed on this player'})
        
        # Get or create wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        # Calculate insurance if requested
        insurance_premium = Decimal('0.00')
        insured_amount = Decimal('0.00')
        
        if insurance_percentage > 0:
            # Create temporary bet object to calculate insurance
            temp_bet = Bet(
                amount_per_run=amount_per_run,
                insurance_percentage=insurance_percentage
            )
            premium, insured_amt = temp_bet.calculate_insurance(estimated_max_runs=100)
            insurance_premium = premium
            insured_amount = insured_amt
            
            # Check if user has enough balance for insurance premium
            if wallet.balance < insurance_premium:
                return JsonResponse({
                    'success': False, 
                    'error': f'Insufficient balance. Insurance premium: ₹{insurance_premium}, Your balance: ₹{wallet.balance}'
                })
            
            # Deduct insurance premium immediately
            wallet.withdraw(insurance_premium)
            Transaction.objects.create(
                user=request.user,
                transaction_type='insurance_premium',
                amount=insurance_premium,
                balance_after=wallet.balance,
                description=f'Insurance premium for bet on {picked_player.player.name}'
            )
        
        # Create bet with insurance details
        bet = Bet.objects.create(
            session=session,
            better=request.user,
            picked_player=picked_player,
            amount_per_run=amount_per_run,
            insurance_percentage=insurance_percentage,
            insurance_premium=insurance_premium,
            insured_amount=insured_amount
        )
        
        # Check if all bets are placed
        total_picks = PickedPlayer.objects.filter(session=session).count()
        total_bets = Bet.objects.filter(session=session).count()
        
        if total_bets >= total_picks:
            session.bets_completed = True
            session.save()
        
        message = f'Bet placed: ₹{amount_per_run} per run'
        if insurance_percentage > 0:
            message += f' (Insurance: {insurance_percentage}%, Premium: ₹{insurance_premium})'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'bets_completed': session.bets_completed,
            'insurance_premium': float(insurance_premium),
            'insured_amount': float(insured_amount)
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
    score_data = cricket_api.get_match_score(session.match.api_id)
    player_stats = score_data.get('player_stats', {})
    
    better_a_total = Decimal('0.00')
    better_b_total = Decimal('0.00')
    
    with db_transaction.atomic():
        # Process all bets
        bets = Bet.objects.filter(session=session, is_settled=False)
        
        for bet in bets:
            player_api_id = bet.picked_player.player.api_id
            player_stat = player_stats.get(player_api_id, {})
            runs_scored = player_stat.get('runs', 0)
            
            # Update bet with runs scored
            bet.runs_scored = runs_scored
            bet.calculate_payout()
            
            # Process insurance if applicable
            insurance_refund = Decimal('0.00')
            if bet.insurance_percentage > 0 and bet.should_claim_insurance(threshold_runs=20):
                # User "lost" (low runs), refund insured amount
                insurance_refund = bet.insured_amount
                bet.insurance_claimed = True
                bet.insurance_refunded = insurance_refund
                
                # Refund insured amount to user's wallet
                wallet = Wallet.objects.get(user=bet.better)
                wallet.deposit(insurance_refund)
                Transaction.objects.create(
                    user=bet.better,
                    transaction_type='insurance_refund',
                    amount=insurance_refund,
                    balance_after=wallet.balance,
                    description=f'Insurance refund for bet on {bet.picked_player.player.name} (scored {runs_scored} runs)'
                )
            
            bet.is_settled = True
            bet.save()
            
            # Update player match stats
            PlayerMatchStats.objects.update_or_create(
                player=bet.picked_player.player,
                match=session.match,
                defaults={'runs_scored': runs_scored}
            )
            
            # Add to respective better's total (payout + insurance refund if applicable)
            total_for_better = bet.total_payout + insurance_refund
            if bet.better == session.better_a:
                better_a_total += total_for_better
            else:
                better_b_total += total_for_better
        
        # Update session totals
        session.better_a_total_winnings = better_a_total
        session.better_b_total_winnings = better_b_total
        session.status = 'completed'
        session.save()
        
        # Update wallets
        wallet_a, _ = Wallet.objects.get_or_create(user=session.better_a)
        wallet_b, _ = Wallet.objects.get_or_create(user=session.better_b)
        
        if better_a_total > 0:
            old_balance = wallet_a.balance
            wallet_a.deposit(better_a_total)
            Transaction.objects.create(
                user=session.better_a,
                transaction_type='bet_won',
                amount=better_a_total,
                balance_after=wallet_a.balance,
                description=f'Won from betting session: {session}'
            )
        
        if better_b_total > 0:
            old_balance = wallet_b.balance
            wallet_b.deposit(better_b_total)
            Transaction.objects.create(
                user=session.better_b,
                transaction_type='bet_won',
                amount=better_b_total,
                balance_after=wallet_b.balance,
                description=f'Won from betting session: {session}'
            )
    
    messages.success(request, "Session settled successfully!")
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