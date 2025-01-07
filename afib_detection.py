import pandas as pd
import pickle
from statistics import mode


# Define the path to the saved Random Forest model
model_path = "training/models/RandomForestClassifier_model.pkl"
with open(model_path, 'rb') as f:
    model = pickle.load(f)


def make_predictions(csv_file):
    df = pd.read_csv(csv_file)
    
    # Drop the "Time" column if it exists
    if "Time" in df.columns:
        df.drop("Time", axis=1, inplace=True)
    predictions = model.predict(df)  # Predict directly on the input data
    return mode(predictions)


# Make predictions using the Random Forest model
# result = make_predictions("combined.csv")
# print(result)


