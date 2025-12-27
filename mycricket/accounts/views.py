from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from core.models import Wallet
from .forms import CustomUserCreationForm
from .models import UserProfile


def signup(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                # Create wallet for the new user
                Wallet.objects.get_or_create(user=user)
                # Ensure profile exists (signal should create it, but ensure it exists)
                UserProfile.objects.get_or_create(user=user)
                # Automatically log in the user after signup
                login(request, user)
                messages.success(request, 'Registration successful! Welcome to CricketSociety!')
                return redirect('core:home')
            except Exception as e:
                # Log the error and show user-friendly message
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error during signup: {str(e)}", exc_info=True)
                messages.error(request, 'An error occurred during registration. Please try again.')
                # Don't redirect, show form again with error
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


class CustomLoginView(LoginView):
    """Custom login view that redirects based on user type"""
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        """Redirect based on user type after login"""
        user = self.request.user
        
        # Master DL (Superuser) - redirect to Master DL dashboard
        if user.is_superuser or user.is_staff:
            return reverse_lazy('core:master_dl_dashboard')
        
        # Check if user has profile
        if hasattr(user, 'profile'):
            profile = user.profile
            if profile.user_type == 'dl':
                # DL User - redirect to DL dashboard
                return reverse_lazy('core:dl_dashboard')
            # End users go to home page
        
        # Default redirect to home page
        return reverse_lazy('core:home')

