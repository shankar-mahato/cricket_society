from django.urls import path
from . import views
from . import job_views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('match/<int:match_id>/', views.match_detail, name='match_detail'),
    path('match/<int:match_id>/create-session/', views.create_betting_session, name='create_betting_session'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('session/<int:session_id>/join/', views.join_betting_session, name='join_betting_session'),
    path('session/<int:session_id>/toss/', views.perform_toss, name='perform_toss'),
    path('session/<int:session_id>/pick-player/', views.pick_player, name='pick_player'),
    path('session/<int:session_id>/check-updates/', views.check_session_updates, name='check_session_updates'),
    path('session/<int:session_id>/place-bet/', views.place_bet, name='place_bet'),
    path('session/<int:session_id>/settle/', views.settle_session, name='settle_session'),
    path('session/<int:session_id>/add-winnings/', views.add_winnings_to_wallet, name='add_winnings_to_wallet'),
    path('session/<int:session_id>/withdraw-winnings/', views.withdraw_winnings, name='withdraw_winnings'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/deposit/', views.deposit_wallet, name='deposit_wallet'),
    # Invite endpoints
    path('session/<int:session_id>/invite/', views.send_invite, name='send_invite'),
    path('session/<int:session_id>/invite/<str:invite_code>/', views.accept_invite, name='accept_invite'),
    path('invites/', views.my_invites, name='my_invites'),
    path('invite/<int:invite_id>/decline/', views.decline_invite, name='decline_invite'),
    path('api/search-users/', views.search_users, name='search_users'),
    # Job endpoint (to prevent 404 errors from polling)
    path('job/check_for_completed_jobs/', job_views.check_for_completed_jobs, name='check_for_completed_jobs'),
]
