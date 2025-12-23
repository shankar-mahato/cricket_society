from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from core.models import Wallet
from .forms import CustomUserCreationForm
from .models import UserProfile


def signup(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create wallet for the new user
            Wallet.objects.get_or_create(user=user)
            # Profile is automatically created via signal
            # Automatically log in the user after signup
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to CricketDuel!')
            return redirect('core:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def profile(request):
    """User profile page"""
    profile_obj, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            profile_obj.profile_picture = request.FILES['profile_picture']
            profile_obj.save()
            messages.success(request, 'Profile picture updated!')
            return redirect('profile')
        if 'bio' in request.POST:
            profile_obj.bio = request.POST.get('bio', '')
            profile_obj.save()
            messages.success(request, 'Bio updated!')
            return redirect('profile')
    
    return render(request, 'accounts/profile.html', {'profile': profile_obj})

