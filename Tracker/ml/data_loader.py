"""
Data loader module for Kaggle menstruation dataset.
Handles downloading, preprocessing, and feature engineering.
"""
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Try to import kagglehub, fallback to sample data if not available
try:
    import kagglehub
    from kagglehub import KaggleDatasetAdapter
    KAGGLE_AVAILABLE = True
except ImportError:
    KAGGLE_AVAILABLE = False


def get_data_dir():
    """Get the data directory path."""
    return Path(__file__).parent / 'data'


def load_kaggle_dataset():
    """
    Load the Kaggle menstruation tracker dataset.
    Returns a pandas DataFrame with the cycle data.
    """
    if not KAGGLE_AVAILABLE:
        print("Warning: kagglehub not installed. Using sample data.")
        return create_sample_data()
    
    try:
        # Load the dataset from Kaggle
        df = kagglehub.load_dataset(
            KaggleDatasetAdapter.PANDAS,
            "anaslari23/mensuration-date-tracker",
            "",  # Empty string loads all CSV files
        )
        return df
    except Exception as e:
        print(f"Warning: Could not load Kaggle dataset: {e}")
        print("Using sample data instead.")
        return create_sample_data()


def create_sample_data():
    """
    Create sample menstruation tracking data for training.
    Used when Kaggle dataset is unavailable.
    """
    np.random.seed(42)
    n_users = 50
    cycles_per_user = 12
    
    data = []
    
    for user_id in range(1, n_users + 1):
        # Each user has a baseline cycle length (21-35 days is normal)
        base_cycle_length = np.random.randint(24, 32)
        # Period length (3-7 days is normal)
        base_period_length = np.random.randint(3, 7)
        
        current_date = pd.Timestamp('2024-01-01') + pd.Timedelta(days=np.random.randint(0, 30))
        
        for cycle_num in range(cycles_per_user):
            # Add some variation to cycle length (+/- 3 days)
            cycle_length = base_cycle_length + np.random.randint(-3, 4)
            cycle_length = max(21, min(35, cycle_length))  # Clamp to normal range
            
            period_length = base_period_length + np.random.randint(-1, 2)
            period_length = max(2, min(8, period_length))
            
            # Symptoms (random but user-consistent)
            has_cramps = np.random.random() > 0.3
            has_headache = np.random.random() > 0.6
            has_mood_swings = np.random.random() > 0.5
            has_fatigue = np.random.random() > 0.4
            has_bloating = np.random.random() > 0.5
            
            # Flow intensity
            flow_choices = ['light', 'medium', 'heavy']
            flow = np.random.choice(flow_choices, p=[0.2, 0.5, 0.3])
            
            data.append({
                'user_id': user_id,
                'cycle_start_date': current_date,
                'cycle_length': cycle_length,
                'period_length': period_length,
                'flow_intensity': flow,
                'cramps': has_cramps,
                'headache': has_headache,
                'mood_swings': has_mood_swings,
                'fatigue': has_fatigue,
                'bloating': has_bloating,
                'age': 20 + (user_id % 20),  # Ages 20-39
            })
            
            current_date = current_date + pd.Timedelta(days=cycle_length)
    
    df = pd.DataFrame(data)
    return df


def preprocess_data(df):
    """
    Preprocess the dataset for model training.
    - Handle missing values
    - Create features for prediction
    - Normalize numerical features
    """
    df = df.copy()
    
    # Convert date columns to datetime if needed
    if 'cycle_start_date' in df.columns:
        df['cycle_start_date'] = pd.to_datetime(df['cycle_start_date'])
    
    # Handle missing values
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    
    # Convert boolean symptoms to int
    bool_cols = ['cramps', 'headache', 'mood_swings', 'fatigue', 'bloating']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(int)
    
    # Encode flow intensity
    if 'flow_intensity' in df.columns:
        flow_map = {'none': 0, 'light': 1, 'medium': 2, 'heavy': 3}
        df['flow_encoded'] = df['flow_intensity'].map(flow_map).fillna(1)
    
    return df


def create_features(df):
    """
    Create features for cycle prediction.
    Uses rolling statistics and lag features.
    """
    df = df.copy()
    
    # Sort by user and date
    if 'user_id' in df.columns and 'cycle_start_date' in df.columns:
        df = df.sort_values(['user_id', 'cycle_start_date'])
    
    # Group by user to calculate rolling features
    if 'user_id' in df.columns:
        # Previous cycle lengths (lag features)
        df['prev_cycle_length_1'] = df.groupby('user_id')['cycle_length'].shift(1)
        df['prev_cycle_length_2'] = df.groupby('user_id')['cycle_length'].shift(2)
        df['prev_cycle_length_3'] = df.groupby('user_id')['cycle_length'].shift(3)
        
        # Rolling mean of last 3 cycles
        df['rolling_mean_3'] = df.groupby('user_id')['cycle_length'].transform(
            lambda x: x.rolling(3, min_periods=1).mean().shift(1)
        )
        
        # Rolling std of last 3 cycles (measure of regularity)
        df['rolling_std_3'] = df.groupby('user_id')['cycle_length'].transform(
            lambda x: x.rolling(3, min_periods=1).std().shift(1)
        )
        
        # Fill NaN with median
        df['rolling_std_3'] = df['rolling_std_3'].fillna(2)  # Default std
    
    # Fill NaN lag features with the current cycle length (for first cycles)
    lag_cols = ['prev_cycle_length_1', 'prev_cycle_length_2', 'prev_cycle_length_3', 'rolling_mean_3']
    for col in lag_cols:
        if col in df.columns:
            df[col] = df[col].fillna(28)  # Default to 28 days
    
    return df


def get_feature_columns():
    """Return the list of feature columns used for prediction."""
    return [
        'prev_cycle_length_1',
        'prev_cycle_length_2', 
        'prev_cycle_length_3',
        'rolling_mean_3',
        'rolling_std_3',
        'age',
        'cramps',
        'headache',
        'mood_swings',
        'fatigue',
        'bloating',
        'flow_encoded',
        'period_length',
    ]


def prepare_training_data():
    """
    Main function to load and prepare data for training.
    Returns X (features) and y (target: cycle_length).
    """
    # Load data
    df = load_kaggle_dataset()
    
    # Preprocess
    df = preprocess_data(df)
    
    # Create features
    df = create_features(df)
    
    # Get feature columns (only those that exist in the dataframe)
    feature_cols = [col for col in get_feature_columns() if col in df.columns]
    
    # Remove rows with missing target
    df = df.dropna(subset=['cycle_length'])
    
    # Prepare X and y
    X = df[feature_cols].fillna(0)
    y = df['cycle_length']
    
    return X, y, feature_cols


if __name__ == '__main__':
    # Test the data loader
    print("Loading and preparing training data...")
    X, y, features = prepare_training_data()
    print(f"Loaded {len(X)} samples with {len(features)} features")
    print(f"Features: {features}")
    print(f"Target stats: mean={y.mean():.1f}, std={y.std():.1f}")
