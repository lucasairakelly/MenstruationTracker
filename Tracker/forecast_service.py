"""
Forecast service for Django integration.
Provides easy-to-use functions for getting cycle predictions.
"""
from datetime import date, timedelta
from typing import Optional, Tuple, List

from .ml.model import predict_with_history


def get_user_cycle_data(user) -> Tuple[List[int], dict]:
    """
    Extract cycle lengths and symptom data from a user's cycles.
    
    Args:
        user: Django User object
    
    Returns:
        cycle_lengths: List of cycle lengths (most recent last)
        symptoms: Dict with aggregated symptom info
    """
    from .models import Cycle, DailyLog
    
    # Get user's completed cycles ordered by date
    cycles = Cycle.objects.filter(
        user=user,
        cycle_length__isnull=False
    ).order_by('start_date')
    
    cycle_lengths = [c.cycle_length for c in cycles if c.cycle_length]
    
    # Aggregate symptoms from daily logs
    symptoms = {
        'cramps': False,
        'headache': False,
        'mood_swings': False,
        'fatigue': False,
        'bloating': False,
        'flow_encoded': 2,  # Default medium
        'period_length': 5,  # Default 5 days
    }
    
    # Get recent logs to determine typical symptoms
    recent_logs = DailyLog.objects.filter(
        cycle__user=user
    ).order_by('-date')[:30]
    
    if recent_logs.exists():
        # Calculate symptom frequency
        symptom_counts = {
            'cramps': sum(1 for l in recent_logs if l.cramps),
            'headache': sum(1 for l in recent_logs if l.headache),
            'mood_swings': sum(1 for l in recent_logs if l.mood_swings),
            'fatigue': sum(1 for l in recent_logs if l.fatigue),
            'bloating': sum(1 for l in recent_logs if l.bloating),
        }
        
        total = len(recent_logs)
        symptoms['cramps'] = symptom_counts['cramps'] > total * 0.3
        symptoms['headache'] = symptom_counts['headache'] > total * 0.3
        symptoms['mood_swings'] = symptom_counts['mood_swings'] > total * 0.3
        symptoms['fatigue'] = symptom_counts['fatigue'] > total * 0.3
        symptoms['bloating'] = symptom_counts['bloating'] > total * 0.3
        
        # Flow intensity
        flow_map = {'none': 0, 'light': 1, 'medium': 2, 'heavy': 3}
        flows = [flow_map.get(l.flow_intensity, 2) for l in recent_logs]
        if flows:
            symptoms['flow_encoded'] = sum(flows) / len(flows)
    
    # Calculate average period length from completed cycles
    if cycles.exists():
        period_lengths = []
        for cycle in cycles:
            if cycle.end_date and cycle.start_date:
                period_length = (cycle.end_date - cycle.start_date).days
                if 1 <= period_length <= 10:  # Reasonable range
                    period_lengths.append(period_length)
        if period_lengths:
            symptoms['period_length'] = sum(period_lengths) / len(period_lengths)
    
    return cycle_lengths, symptoms


def get_prediction_for_user(user) -> dict:
    """
    Get cycle prediction for a user.
    
    Args:
        user: Django User object
    
    Returns:
        dict with prediction info:
        - predicted_length: Predicted cycle length in days
        - predicted_date: Predicted next period start date
        - confidence: Confidence score (0-1)
        - days_until: Days until predicted start
        - has_enough_data: Whether user has enough cycles for prediction
    """
    cycle_lengths, symptoms = get_user_cycle_data(user)
    
    # Check if user has enough data
    has_enough_data = len(cycle_lengths) >= 1
    
    if not has_enough_data:
        return {
            'predicted_length': None,
            'predicted_date': None,
            'confidence': 0,
            'days_until': None,
            'has_enough_data': False,
            'message': 'Log at least one complete cycle to get predictions'
        }
    
    # Get user age (default to 25 if not available)
    user_age = 25  # Could be extended with user profile
    
    # Make prediction
    predicted_length, confidence = predict_with_history(
        cycle_lengths, 
        user_age=user_age, 
        symptoms=symptoms
    )
    
    # Calculate predicted date based on last cycle
    from .models import Cycle
    last_cycle = Cycle.objects.filter(user=user).order_by('-start_date').first()
    
    if last_cycle:
        if last_cycle.end_date:
            # Use end date + predicted length
            predicted_date = last_cycle.start_date + timedelta(days=int(predicted_length))
        else:
            # Ongoing cycle - use start date + predicted length
            predicted_date = last_cycle.start_date + timedelta(days=int(predicted_length))
        
        days_until = (predicted_date - date.today()).days
    else:
        predicted_date = None
        days_until = None
    
    # Adjust confidence based on data quality
    if len(cycle_lengths) < 3:
        confidence *= 0.7  # Lower confidence with less data
    
    # Generate message based on confidence
    if confidence >= 0.7:
        message = "High confidence prediction"
    elif confidence >= 0.5:
        message = "Moderate confidence - log more cycles for better accuracy"
    else:
        message = "Low confidence - based on limited data"
    
    return {
        'predicted_length': predicted_length,
        'predicted_date': predicted_date,
        'confidence': round(confidence, 2),
        'days_until': days_until,
        'has_enough_data': True,
        'message': message,
        'cycle_count': len(cycle_lengths)
    }
