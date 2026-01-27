from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import Cycle, DailyLog
from .forms import CycleForm, DailyLogForm
from .forecast_service import get_prediction_for_user

# ========== AUTHENTICATION VIEWS ==========

def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'pages/login.html')

def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

def user_register(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validation
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        elif len(password1) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        else:
            # Create user
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.save()
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')
    
    return render(request, 'pages/register.html')

# ========== MAIN VIEWS (PROTECTED) ==========

@login_required(login_url='login')
def home(request):
    # Filter cycles by logged-in user only
    cycles = Cycle.objects.filter(user=request.user)[:5]
    total_cycles = Cycle.objects.filter(user=request.user).count()

    # FIX: Check if the latest cycle was prematurely closed (likely user error thinking "End Date" = "End of Period")
    # If the latest cycle is very short (< 7 days) and has an end date, we re-open it.
    latest_cycle = Cycle.objects.filter(user=request.user).order_by('-start_date').first()
    if latest_cycle and latest_cycle.end_date and latest_cycle.cycle_length and latest_cycle.cycle_length < 7:
        latest_cycle.end_date = None
        latest_cycle.cycle_length = None
        latest_cycle.save()
    
    # Calculate actual stats
    all_cycles = Cycle.objects.filter(user=request.user, cycle_length__isnull=False)
    if all_cycles.exists():
        avg_length = sum(c.cycle_length for c in all_cycles) / all_cycles.count()
        avg_cycle = f"{avg_length:.0f} days"
        days_tracked = sum(c.cycle_length for c in all_cycles if c.cycle_length)
    else:
        avg_cycle = "N/A"
        days_tracked = 0
    
    # Calculate current day in cycle
    last_cycle = Cycle.objects.filter(user=request.user).order_by('-start_date').first()
    if last_cycle and not last_cycle.end_date:
        from datetime import date
        current_day = (date.today() - last_cycle.start_date).days + 1
    else:
        current_day = "-"
    
    # Get forecast prediction
    forecast = get_prediction_for_user(request.user)
    
    context = {
        'cycles': cycles,
        'total_cycles': total_cycles,
        'avg_cycle': avg_cycle,
        'current_day': current_day,
        'days_tracked': days_tracked,
        'forecast': forecast,
    }
    return render(request, 'pages/home.html', context)

# ========== CYCLE CRUD ==========

@login_required(login_url='login')
def cycle_create(request):
    if request.method == 'POST':
        form = CycleForm(request.POST)
        if form.is_valid():
            cycle = form.save(commit=False)
            # Automatically close the previous cycle if it's still open
            previous_cycle = Cycle.objects.filter(user=request.user).order_by('-start_date').first()
            if previous_cycle and not previous_cycle.end_date:
                from datetime import timedelta
                # Set end date to the day before the new cycle starts
                previous_cycle.end_date = cycle.start_date - timedelta(days=1)
                previous_cycle.save()  # This will now auto-calculate length
            
            cycle.user = request.user  # Assign current user
            cycle.save()
            messages.success(request, 'Cycle created successfully!')
            return redirect('home')
    else:
        form = CycleForm()
    
    return render(request, 'pages/cycle_form.html', {'form': form, 'action': 'Create'})

@login_required(login_url='login')
def cycle_detail(request, pk):
    # Only allow user to see their own cycles
    cycle = get_object_or_404(Cycle, pk=pk, user=request.user)
    daily_logs = cycle.daily_logs.all().order_by('-date')
    return render(request, 'pages/cycle_detail.html', {'cycle': cycle, 'daily_logs': daily_logs})

@login_required(login_url='login')
def cycle_update(request, pk):
    # Only allow user to edit their own cycles
    cycle = get_object_or_404(Cycle, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CycleForm(request.POST, instance=cycle)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cycle updated successfully!')
            return redirect('cycle_detail', pk=cycle.pk)
    else:
        form = CycleForm(instance=cycle)
    
    return render(request, 'pages/cycle_form.html', {'form': form, 'action': 'Update', 'cycle': cycle})

@login_required(login_url='login')
def cycle_delete(request, pk):
    # Only allow user to delete their own cycles
    cycle = get_object_or_404(Cycle, pk=pk, user=request.user)
    if request.method == 'POST':
        cycle.delete()
        messages.success(request, 'Cycle deleted successfully!')
        return redirect('home')
    
    return render(request, 'pages/cycle_confirm_delete.html', {'cycle': cycle})


# ========== FORECAST API ==========

@login_required(login_url='login')
def forecast_view(request):
    """
    API endpoint to get cycle forecast prediction.
    Returns JSON with prediction data.
    """
    forecast = get_prediction_for_user(request.user)
    
    # Convert date to string for JSON serialization
    if forecast.get('predicted_date'):
        forecast['predicted_date'] = forecast['predicted_date'].isoformat()
    
    return JsonResponse(forecast)


# ========== ANALYTICS ==========

@login_required(login_url='login')
def analytics_view(request):
    """
    Analytics page showing cycle history, charts, and predictions.
    """
    # Get all user cycles
    # Self-healing: Fix existing cycles with end dates but no length
    # This addresses the user's current issue where they have data but it's not processing
    broken_cycles = Cycle.objects.filter(user=request.user, cycle_length__isnull=True, end_date__isnull=False)
    for broken_cycle in broken_cycles:
        broken_cycle.save()  # Triggers the new calculate logic in model.save()

    # Get all user cycles
    cycles = Cycle.objects.filter(user=request.user).order_by('-start_date')
    
    # Get cycles with lengths for statistics
    complete_cycles = Cycle.objects.filter(
        user=request.user, 
        cycle_length__isnull=False
    )
    
    # Calculate statistics
    if complete_cycles.exists():
        lengths = [c.cycle_length for c in complete_cycles]
        avg_cycle_length = sum(lengths) / len(lengths)
        min_cycle_length = min(lengths)
        max_cycle_length = max(lengths)
    else:
        avg_cycle_length = 0
        min_cycle_length = 0
        max_cycle_length = 0
    
    # Get forecast
    forecast = get_prediction_for_user(request.user)
    
    # Convert confidence to percentage for display
    if forecast.get('confidence'):
        forecast['confidence'] = forecast['confidence'] * 100
    
    # Calculate symptom statistics from daily logs
    all_logs = DailyLog.objects.filter(cycle__user=request.user)
    total_logs = all_logs.count()
    
    symptom_stats = {
        'total_logs': total_logs,
        'cramps_count': all_logs.filter(cramps=True).count(),
        'headache_count': all_logs.filter(headache=True).count(),
        'mood_swings_count': all_logs.filter(mood_swings=True).count(),
        'fatigue_count': all_logs.filter(fatigue=True).count(),
        'bloating_count': all_logs.filter(bloating=True).count(),
    }
    
    # Calculate percentages
    if total_logs > 0:
        symptom_stats['cramps_pct'] = round(symptom_stats['cramps_count'] / total_logs * 100)
        symptom_stats['headache_pct'] = round(symptom_stats['headache_count'] / total_logs * 100)
        symptom_stats['mood_swings_pct'] = round(symptom_stats['mood_swings_count'] / total_logs * 100)
        symptom_stats['fatigue_pct'] = round(symptom_stats['fatigue_count'] / total_logs * 100)
        symptom_stats['bloating_pct'] = round(symptom_stats['bloating_count'] / total_logs * 100)
    else:
        symptom_stats['cramps_pct'] = 0
        symptom_stats['headache_pct'] = 0
        symptom_stats['mood_swings_pct'] = 0
        symptom_stats['fatigue_pct'] = 0
        symptom_stats['bloating_pct'] = 0
    
    # Flow intensity breakdown
    flow_stats = {
        'none': all_logs.filter(flow_intensity='none').count(),
        'light': all_logs.filter(flow_intensity='light').count(),
        'medium': all_logs.filter(flow_intensity='medium').count(),
        'heavy': all_logs.filter(flow_intensity='heavy').count(),
    }
    
    context = {
        'cycles': cycles,
        'forecast': forecast,
        'avg_cycle_length': avg_cycle_length,
        'min_cycle_length': min_cycle_length,
        'max_cycle_length': max_cycle_length,
        'symptom_stats': symptom_stats,
        'flow_stats': flow_stats,
    }
    
    return render(request, 'pages/analytics.html', context)


# ========== DAILY LOG CRUD ==========

@login_required(login_url='login')
def daily_log_create(request, cycle_pk):
    """Create a daily log entry for a specific cycle."""
    cycle = get_object_or_404(Cycle, pk=cycle_pk, user=request.user)
    
    if request.method == 'POST':
        form = DailyLogForm(request.POST)
        if form.is_valid():
            daily_log = form.save(commit=False)
            daily_log.cycle = cycle
            daily_log.save()
            messages.success(request, 'Daily log added successfully!')
            return redirect('cycle_detail', pk=cycle.pk)
    else:
        from datetime import date
        form = DailyLogForm(initial={'date': date.today()})
    
    return render(request, 'pages/daily_log_form.html', {
        'form': form, 
        'cycle': cycle,
        'action': 'Add'
    })


@login_required(login_url='login')
def daily_log_update(request, cycle_pk, log_pk):
    """Update a daily log entry."""
    cycle = get_object_or_404(Cycle, pk=cycle_pk, user=request.user)
    daily_log = get_object_or_404(DailyLog, pk=log_pk, cycle=cycle)
    
    if request.method == 'POST':
        form = DailyLogForm(request.POST, instance=daily_log)
        if form.is_valid():
            form.save()
            messages.success(request, 'Daily log updated successfully!')
            return redirect('cycle_detail', pk=cycle.pk)
    else:
        form = DailyLogForm(instance=daily_log)
    
    return render(request, 'pages/daily_log_form.html', {
        'form': form, 
        'cycle': cycle,
        'daily_log': daily_log,
        'action': 'Update'
    })


@login_required(login_url='login')
def daily_log_delete(request, cycle_pk, log_pk):
    """Delete a daily log entry."""
    cycle = get_object_or_404(Cycle, pk=cycle_pk, user=request.user)
    daily_log = get_object_or_404(DailyLog, pk=log_pk, cycle=cycle)
    
    if request.method == 'POST':
        daily_log.delete()
        messages.success(request, 'Daily log deleted successfully!')
        return redirect('cycle_detail', pk=cycle.pk)
    
    return render(request, 'pages/daily_log_confirm_delete.html', {
        'daily_log': daily_log,
        'cycle': cycle
    })