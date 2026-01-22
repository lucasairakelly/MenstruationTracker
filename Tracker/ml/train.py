"""
Training script for the cycle prediction model.
Run with: python -m Tracker.ml.train
"""
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from Tracker.ml.data_loader import prepare_training_data
from Tracker.ml.model import train_model, save_model


def main():
    print("=" * 50)
    print("Cycle Prediction Model Training")
    print("=" * 50)
    
    # Step 1: Load and prepare data
    print("\n[1/3] Loading and preparing training data...")
    try:
        X, y, feature_names = prepare_training_data()
        print(f"     ✓ Loaded {len(X)} samples with {len(feature_names)} features")
    except Exception as e:
        print(f"     ✗ Error loading data: {e}")
        return 1
    
    # Step 2: Train model
    print("\n[2/3] Training Random Forest model...")
    try:
        model, metrics = train_model(X, y)
        print(f"     ✓ Training complete!")
        print(f"       - Train MAE: {metrics['train_mae']:.2f} days")
        print(f"       - Test MAE:  {metrics['test_mae']:.2f} days")
        print(f"       - Train R²:  {metrics['train_r2']:.3f}")
        print(f"       - Test R²:   {metrics['test_r2']:.3f}")
    except Exception as e:
        print(f"     ✗ Error training model: {e}")
        return 1
    
    # Step 3: Save model
    print("\n[3/3] Saving model...")
    try:
        save_model(model, feature_names)
        print("     ✓ Model saved successfully!")
    except Exception as e:
        print(f"     ✗ Error saving model: {e}")
        return 1
    
    print("\n" + "=" * 50)
    print("Training completed successfully!")
    print("=" * 50)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
