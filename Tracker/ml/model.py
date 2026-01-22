"""
Cycle prediction model module.
Uses Random Forest to predict next cycle length.
"""
import os
import joblib
import numpy as np
from pathlib import Path

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def get_model_path():
    """Get the path to the saved model file."""
    return Path(__file__).parent / 'models' / 'cycle_predictor.joblib'


def train_model(X, y, test_size=0.2, random_state=42):
    """
    Train a Random Forest model for cycle length prediction.
    
    Args:
        X: Feature DataFrame/array
        y: Target array (cycle lengths)
        test_size: Fraction of data to use for testing
        random_state: Random seed for reproducibility
    
    Returns:
        model: Trained RandomForestRegressor
        metrics: Dictionary with training metrics
    """
    if not SKLEARN_AVAILABLE:
        raise ImportError("scikit-learn is required. Install with: pip install scikit-learn")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    
    # Train model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    metrics = {
        'train_mae': mean_absolute_error(y_train, y_pred_train),
        'test_mae': mean_absolute_error(y_test, y_pred_test),
        'train_r2': r2_score(y_train, y_pred_train),
        'test_r2': r2_score(y_test, y_pred_test),
        'n_train': len(X_train),
        'n_test': len(X_test),
    }
    
    return model, metrics


def save_model(model, feature_names):
    """
    Save the trained model and feature names to disk.
    
    Args:
        model: Trained model
        feature_names: List of feature column names
    """
    model_path = get_model_path()
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        'model': model,
        'feature_names': feature_names,
        'version': '1.0'
    }
    
    joblib.dump(model_data, model_path)
    print(f"Model saved to {model_path}")


def load_model():
    """
    Load the trained model from disk.
    
    Returns:
        model: Trained model
        feature_names: List of feature column names
    """
    model_path = get_model_path()
    
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. "
            "Run 'python -m Tracker.ml.train' to train the model first."
        )
    
    model_data = joblib.load(model_path)
    return model_data['model'], model_data['feature_names']


def predict_cycle_length(features_dict):
    """
    Predict the next cycle length given user features.
    
    Args:
        features_dict: Dictionary with feature values
    
    Returns:
        predicted_length: Predicted cycle length in days
        confidence: Confidence score (0-1)
    """
    model, feature_names = load_model()
    
    # Prepare features array
    features = []
    for name in feature_names:
        value = features_dict.get(name, 0)
        if value is None:
            value = 0
        features.append(float(value))
    
    features_array = np.array(features).reshape(1, -1)
    
    # Make prediction
    predicted_length = model.predict(features_array)[0]
    
    # Clamp to reasonable range (21-40 days)
    predicted_length = max(21, min(40, predicted_length))
    
    # Calculate confidence based on feature availability
    available_features = sum(1 for name in feature_names if features_dict.get(name) is not None)
    confidence = available_features / len(feature_names)
    
    return round(predicted_length, 1), confidence


def predict_with_history(cycle_lengths, user_age=25, symptoms=None):
    """
    Predict next cycle length based on user's cycle history.
    
    Args:
        cycle_lengths: List of previous cycle lengths (most recent last)
        user_age: User's age
        symptoms: Dict with symptom info (cramps, headache, etc.)
    
    Returns:
        predicted_length: Predicted cycle length in days
        confidence: Confidence score (0-1)
    """
    if symptoms is None:
        symptoms = {}
    
    # Calculate rolling statistics from history
    if len(cycle_lengths) >= 3:
        prev_1 = cycle_lengths[-1]
        prev_2 = cycle_lengths[-2]
        prev_3 = cycle_lengths[-3]
        rolling_mean = np.mean(cycle_lengths[-3:])
        rolling_std = np.std(cycle_lengths[-3:])
    elif len(cycle_lengths) >= 2:
        prev_1 = cycle_lengths[-1]
        prev_2 = cycle_lengths[-2]
        prev_3 = cycle_lengths[-1]  # Fallback
        rolling_mean = np.mean(cycle_lengths)
        rolling_std = np.std(cycle_lengths) if len(cycle_lengths) > 1 else 2
    elif len(cycle_lengths) == 1:
        prev_1 = prev_2 = prev_3 = cycle_lengths[0]
        rolling_mean = cycle_lengths[0]
        rolling_std = 2
    else:
        # No history - use defaults
        prev_1 = prev_2 = prev_3 = 28
        rolling_mean = 28
        rolling_std = 2
    
    features = {
        'prev_cycle_length_1': prev_1,
        'prev_cycle_length_2': prev_2,
        'prev_cycle_length_3': prev_3,
        'rolling_mean_3': rolling_mean,
        'rolling_std_3': rolling_std,
        'age': user_age,
        'cramps': 1 if symptoms.get('cramps') else 0,
        'headache': 1 if symptoms.get('headache') else 0,
        'mood_swings': 1 if symptoms.get('mood_swings') else 0,
        'fatigue': 1 if symptoms.get('fatigue') else 0,
        'bloating': 1 if symptoms.get('bloating') else 0,
        'flow_encoded': symptoms.get('flow_encoded', 2),
        'period_length': symptoms.get('period_length', 5),
    }
    
    try:
        return predict_cycle_length(features)
    except FileNotFoundError:
        # Model not trained yet - use simple average
        if cycle_lengths:
            return round(np.mean(cycle_lengths), 1), 0.5
        return 28.0, 0.3
