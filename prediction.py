import pandas as pd
import numpy as np 
import os
from sklearn.linear_model import LinearRegression

def load_attendance_data(file_path):
    """
    Loads and cleans the attendance dataset.
    
    Args:
        file_path (str): Path to the attendance CSV file.
        
    Returns:
        pandas.DataFrame: Cleaned attendance data.
    """
    try:
        # 1. Even though it's called .xls, the user hinted and inspecting it proved it's a CSV format.
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Could not load data from {file_path}. Error: {e}")
        
    # 2. Validate required columns exist
    required_columns = ['student_id', 'subject', 'week', 'attendance_percentage']
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        raise ValueError(f"Missing required columns in dataset: {missing_cols}")
        
    # 3. Drop phone_number as requested, but keep metadata (name, etc.)
    cols_to_drop = ['phone_number']
    existing_cols_to_drop = [col for col in cols_to_drop if col in df.columns]
    if existing_cols_to_drop:
        df = df.drop(columns=existing_cols_to_drop)
        
    # Ensure numeric types where appropriate
    df['attendance_percentage'] = pd.to_numeric(df['attendance_percentage'], errors='coerce')
    
    # 4. Extract numeric week number from values like "Week 1"
    df['week'] = df['week'].astype(str).str.extract(r'(\d+)')[0].astype(float)
    
    df['week'] = pd.to_numeric(df['week'], errors='coerce')
    
    # Check for missing values
    if df[['week', 'attendance_percentage']].isnull().any().any():
        df = df.dropna(subset=['week', 'attendance_percentage'])
        
    # 5. Sort the DataFrame by student_id, subject, numeric week
    df = df.sort_values(by=['student_id', 'subject', 'week'])
    
    # 7. Return cleaned DataFrame
    return df.reset_index(drop=True)

def calculate_trend(attendance_values):
    """
    Calculates the linear slope of attendance over time using numpy.polyfit.
    
    Args:
        attendance_values (list, pandas Series, or numpy array): Chronological sequence of attendance percentages.
        
    Returns:
        float: The calculated linear slope.
    """
    try:
        y = np.array(attendance_values, dtype=float)
    except (ValueError, TypeError):
        raise ValueError("attendance_values must be convertible to a numeric array.")
        
    # Require at least 2 valid values
    if len(y) < 2:
        raise ValueError("At least 2 attendance values are required to calculate a trend.")
        
    # Generate chronological indexes based on the length
    x = np.arange(len(y))
    
    # Calculate slope (degree=1 polynomial)
    slope, intercept = np.polyfit(x, y, 1)
    
    return float(slope)

def get_trend_direction(slope):
    """
    Classifies the attendance trend direction based on the calculated slope.
    
    Args:
        slope (float): The numerical slope from calculate_trend.
        
    Returns:
        str: 'IMPROVING', 'DECLINING', or 'STABLE'.
    """
    if slope > 0.5:
        return 'IMPROVING'
    elif slope < -0.5:
        return 'DECLINING'
    else:
        return 'STABLE'

def predict_future_attendance(attendance_values, periods_ahead=4):
    """
    Predicts future attendance using linear regression.
    
    Args:
        attendance_values (list, pandas Series, or numpy array): Chronological sequence of attendance percentages.
        periods_ahead (int): Number of periods into the future to predict.
        
    Returns:
        tuple: (list of predicted_attendance, float regression_slope)
    """
    try:
        y = np.array(attendance_values, dtype=float)
    except (ValueError, TypeError):
        raise ValueError("attendance_values must be convertible to a numeric array.")
        
    # Handle insufficient data safely
    if len(y) < 2:
        raise ValueError("At least 2 attendance values are required for prediction.")
        
    # 2. Use chronological index positions as the time feature X
    X = np.arange(len(y)).reshape(-1, 1)
    
    # 4. Train the model
    model = LinearRegression()
    model.fit(X, y)
    
    # 5. Predict attendance periods_ahead into the future
    future_X = np.arange(len(y), len(y) + periods_ahead).reshape(-1, 1)
    predicted_attendance = model.predict(future_X)
    
    # 7. Clamp predicted_attendance between 0 and 100
    predicted_attendance = np.clip(predicted_attendance, 0, 100).round(1).tolist()
    
    regression_slope = float(model.coef_[0])
    
    # 6. Return predicted_attendance and regression_slope
    return predicted_attendance, regression_slope

def classify_risk(current_attendance, predicted_attendance, trend_slope, threshold=85):
    """
    Classifies the attendance risk into HIGH, MEDIUM, or LOW and calculates a numerical risk score.
    
    Args:
        current_attendance (float): Current attendance percentage.
        predicted_attendance (float): Predicted future attendance percentage.
        trend_slope (float): The numerical trend slope.
        threshold (float): The attendance threshold for intervention (default 85).
        
    Returns:
        tuple: (str risk_level, float risk_score [0-100])
    """
    # -- RISK LEVEL CLASSIFICATION --
    
    # HIGH RISK: 
    # - Current attendance is already breached (below 85) OR
    # - EARLY WARNING: Current is >= 85, but it is predicted to fall below 85.
    if current_attendance < threshold or (current_attendance >= threshold and predicted_attendance < threshold):
        risk_level = 'HIGH'
        
    # LOW RISK:
    # - Current is safe (>90) AND predicted is safe (>90) AND trend is not significantly declining (slope >= -0.5)
    elif current_attendance > 90 and predicted_attendance > 90 and trend_slope >= -0.5:
        risk_level = 'LOW'
        
    # MEDIUM RISK:
    # - Catch-all for scenarios where attendance is between 85-90, predicted is between 85-90, 
    #   or there's a significant decline (slope < -0.5) but it hasn't triggered the HIGH risk threshold yet.
    else:
        risk_level = 'MEDIUM'
        
    # -- RISK SCORE CALCULATION --
    # Calculate a raw risk metric where lower attendance = higher risk.
    # We heavily weight the predicted attendance to prioritize early warning.
    raw_score = ((100 - current_attendance) * 0.4) + ((100 - predicted_attendance) * 0.6) - (trend_slope * 3.0)
    
    # Normalize and clamp the score based on the assigned level to make it highly interpretable (0-100 scale)
    if risk_level == 'HIGH':
        risk_score = max(75.0, min(100.0, raw_score + 60.0))
    elif risk_level == 'MEDIUM':
        risk_score = max(40.0, min(74.9, raw_score + 35.0))
    else:
        risk_score = max(0.0, min(39.9, raw_score))
        
    return risk_level, round(risk_score, 1)

def analyze_student_attendance(attendance_values, periods_ahead=4, threshold=85):
    """
    Analyzes student attendance history to generate trends, predictions, and risk classifications.
    
    Args:
        attendance_values (list, pandas Series, or numpy array): Chronological attendance history.
        periods_ahead (int): Number of periods into the future to predict (default 4).
        threshold (float): The attendance threshold for intervention (default 85).
        
    Returns:
        dict: Analysis results.
    """
    # 1. Validate the attendance history
    try:
        y = np.array(attendance_values, dtype=float)
    except (ValueError, TypeError):
        raise ValueError("attendance_values must be convertible to a numeric array.")
        
    if len(y) < 2:
        raise ValueError("At least 2 attendance values are required for analysis.")
        
    # 2. Get the latest attendance as current_attendance
    current_attendance = float(y[-1])
    
    # 3 & 4. Calculate trend slope and direction
    trend_slope = calculate_trend(y)
    trend_direction = get_trend_direction(trend_slope)
    
    # 5. Predict future attendance
    future_predictions, _ = predict_future_attendance(y, periods_ahead=periods_ahead)
    predicted_attendance = future_predictions[-1]
    
    # 6 & 7. Calculate risk_score and risk_level
    risk_level, risk_score = classify_risk(
        current_attendance, 
        predicted_attendance, 
        trend_slope, 
        threshold=threshold
    )
    
    # Return numerical results rounded appropriately
    return {
        "current_attendance": round(current_attendance, 2),
        "trend_slope": round(trend_slope, 2),
        "trend_direction": trend_direction,
        "predicted_attendance": round(predicted_attendance, 2),
        "risk_score": risk_score,
        "risk_level": risk_level
    }

def analyze_all_students(df, periods_ahead=4, threshold=85):
    """
    Analyzes attendance for all students and subjects in the dataset.
    
    Args:
        df (pandas.DataFrame): The cleaned attendance DataFrame.
        periods_ahead (int): Number of periods into the future to predict.
        threshold (float): The attendance threshold for intervention.
        
    Returns:
        pandas.DataFrame: A new DataFrame with the analysis results per student/subject.
    """
    results = []
    
    # 1. Group by student_id and subject
    grouped = df.groupby(['student_id', 'subject'])
    
    for (student, subject), group in grouped:
        # 2. Sort every group by week
        group = group.sort_values(by='week')
        
        # 3. Extract attendance_percentage as chronological history
        history = group['attendance_percentage'].tolist()
        
        # Extract student metadata (take from the first row of the group)
        name = group['name'].iloc[0] if 'name' in group.columns else "Unknown"
        section = group['section'].iloc[0] if 'section' in group.columns else "Unknown"
        branch = group['branch'].iloc[0] if 'branch' in group.columns else "Unknown"
        semester = group['semester'].iloc[0] if 'semester' in group.columns else "Unknown"
        
        # 6. Handle groups with insufficient history safely
        try:
            # 4. Run analyze_student_attendance
            analysis = analyze_student_attendance(
                history, 
                periods_ahead=periods_ahead, 
                threshold=threshold
            )
            
            # Combine identifiers with the analysis dictionary
            row = {
                'student_id': student,
                'name': name,
                'section': section,
                'branch': branch,
                'semester': semester,
                'subject': subject,
                **analysis
            }
            results.append(row)
        except Exception as e:
            print(f"Warning: Could not analyze {student} - {subject}. Reason: {e}")
            
    # 5. Build and return a new pandas DataFrame (satisfies rule 7: don't modify original)
    return pd.DataFrame(results)

if __name__ == "__main__":
    # Define input and output paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(base_dir, "data", "attendance_dataset.csv")
    output_csv = os.path.join(base_dir, "prediction_results.csv")
    
    if os.path.exists(input_csv):
        # 1. Load the sample attendance data
        print(f"Loading dataset from {input_csv}...")
        df = load_attendance_data(input_csv)
        print(f"Dataset loaded with {len(df)} records.\n")
        
        print("--- Dataset Verification ---")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print("\nFirst 5 rows:")
        print(df.head().to_string())
        print("----------------------------\n")
        
        # 2. Run analyze_all_students
        print("Running batch analysis across all students and subjects...")
        results_df = analyze_all_students(df)
        
        # 4. Sort results by risk_score from highest to lowest
        results_df = results_df.sort_values(by='risk_score', ascending=False).reset_index(drop=True)
        
        # 3. Extract the Early Warning students
        early_warning_df = results_df[
            (results_df['current_attendance'] >= 85) & 
            (results_df['predicted_attendance'] < 85)
        ]
        
        # 4. Save the main DataFrame
        results_df.to_csv(output_csv, index=False)
        
        # 5. Save the early warning DataFrame
        early_warning_csv = os.path.join(base_dir, "early_warning_students.csv")
        early_warning_df.to_csv(early_warning_csv, index=False)
        
        # 6. Print confirmation
        print("\n--- Final Save Confirmation ---")
        print(f"Saved {len(results_df)} total prediction records to: {os.path.basename(output_csv)}")
        print(f"Saved {len(early_warning_df)} early warning students to: {os.path.basename(early_warning_csv)}")
        print("-------------------------------")
        
        # 7. Print a summary containing counts
        total_analyzed = len(results_df)
        high_count = len(results_df[results_df['risk_level'] == 'HIGH'])
        medium_count = len(results_df[results_df['risk_level'] == 'MEDIUM'])
        low_count = len(results_df[results_df['risk_level'] == 'LOW'])
        
        print("\n--- Prediction Summary ---")
        print(f"Total Records Analyzed: {total_analyzed}")
        print(f"HIGH Risk Count:        {high_count}")
        print(f"MEDIUM Risk Count:      {medium_count}")
        print(f"LOW Risk Count:         {low_count}")
        print("--------------------------\n")
    else:
        print(f"Error: Input dataset not found at {input_csv}")


