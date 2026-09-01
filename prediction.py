"""
Attendance Risk Prediction System

Purpose:
Analyze historical attendance trends and predict whether a student is at risk of falling below the required 75 percent attendance threshold.

Main Feature:
Early warning for students who are currently above 75 percent but are predicted to fall below 75 percent.
"""

# ==================================================
# 1. IMPORTS
# ==================================================
import os
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression


# ==================================================
# 2. CONFIGURATION
# ==================================================
ATTENDANCE_THRESHOLD = 75
PREDICTION_PERIODS = 4


# ==================================================
# 3. DATA LOADING AND VALIDATION
# ==================================================
def load_attendance_data(file_path):
    """
    Loads and validates the real attendance dataset.
    
    Required Columns:
    - student_id
    - subject
    - week
    - attendance_percentage
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Could not load data from {file_path}. Error: {e}")
        
    required_columns = ['student_id', 'subject', 'week', 'attendance_percentage']
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
        
    # Drop unnecessary columns
    if 'phone_number' in df.columns:
        df = df.drop(columns=['phone_number'])
        
    # Ensure attendance is numeric
    df['attendance_percentage'] = pd.to_numeric(df['attendance_percentage'], errors='coerce')
    
    # Convert 'Week X' strings into chronological numeric order (1.0, 2.0...)
    df['week'] = df['week'].astype(str).str.extract(r'(\d+)')[0].astype(float)
    df['week'] = pd.to_numeric(df['week'], errors='coerce')
    
    # Drop rows with invalid week or attendance
    if df[['week', 'attendance_percentage']].isnull().any().any():
        df = df.dropna(subset=['week', 'attendance_percentage'])
        
    # Sort data chronologically to ensure accurate trend analysis
    df = df.sort_values(by=['student_id', 'subject', 'week'])
    
    return df.reset_index(drop=True)


# ==================================================
# 4. TREND ANALYSIS
# ==================================================
def calculate_trend(attendance_values):
    """
    Calculates linear slope over time.
    """
    y = np.array(attendance_values, dtype=float)
    if len(y) < 2:
        raise ValueError("At least 2 values are required.")
        
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    
    return float(slope)


def get_trend_direction(slope):
    """
    Interprets the slope direction:
    positive slope = improving attendance
    negative slope = declining attendance
    near-zero slope = stable attendance
    """
    if slope > 0.5:
        return 'IMPROVING'
    elif slope < -0.5:
        return 'DECLINING'
    else:
        return 'STABLE'


# ==================================================
# 5. FUTURE ATTENDANCE PREDICTION
# ==================================================
def predict_future_attendance(attendance_values, periods_ahead=PREDICTION_PERIODS):
    """
    Uses Linear Regression to predict future attendance.
    
    - X represents chronological time steps.
    - y represents historical attendance percentages.
    - Linear Regression captures the linear trend effectively over small time series.
    """
    y = np.array(attendance_values, dtype=float)
    if len(y) < 2:
        raise ValueError("At least 2 values are required.")
        
    X = np.arange(len(y)).reshape(-1, 1)
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict future attendance steps
    future_X = np.arange(len(y), len(y) + periods_ahead).reshape(-1, 1)
    predicted_attendance = model.predict(future_X)
    
    # Limit predictions between 0 and 100 since attendance cannot exceed those bounds
    predicted_attendance = np.clip(predicted_attendance, 0, 100).round(1).tolist()
    
    regression_slope = float(model.coef_[0])
    
    return predicted_attendance, regression_slope


# ==================================================
# 6. RISK CLASSIFICATION
# ==================================================
def classify_risk(current_attendance, predicted_attendance, trend_slope, threshold=ATTENDANCE_THRESHOLD):
    """
    Classifies risk based on the 75 percent threshold.
    """
    # HIGH RISK: Already below 75%
    if current_attendance < threshold:
        risk_level = 'HIGH'
        
    # HIGH RISK — EARLY WARNING: Currently >= 75% but predicted to drop below 75%
    elif current_attendance >= threshold and predicted_attendance < threshold:
        risk_level = 'HIGH'
        
    # LOW RISK: Safe and stable
    elif current_attendance > (threshold + 5) and predicted_attendance > (threshold + 5) and trend_slope >= -0.5:
        risk_level = 'LOW'
        
    # MEDIUM RISK: Warning zone or declining but not yet HIGH
    else:
        risk_level = 'MEDIUM'
        
    # Calculate an interpretable 0-100 risk score
    raw_score = ((100 - current_attendance) * 0.4) + ((100 - predicted_attendance) * 0.6) - (trend_slope * 3.0)
    
    if risk_level == 'HIGH':
        risk_score = max(75.0, min(100.0, raw_score + 60.0))
    elif risk_level == 'MEDIUM':
        risk_score = max(40.0, min(74.9, raw_score + 35.0))
    else:
        risk_score = max(0.0, min(39.9, raw_score))
        
    return risk_level, round(risk_score, 1)


# ==================================================
# 7. ANALYZE ONE STUDENT
# ==================================================
def analyze_student_attendance(attendance_values, periods_ahead=PREDICTION_PERIODS, threshold=ATTENDANCE_THRESHOLD):
    """
    Analyzes one student's attendance history and generates a prediction.
    """
    y = np.array(attendance_values, dtype=float)
    if len(y) < 2:
        raise ValueError("Insufficient data.")
        
    # Attendance History -> Current Attendance
    current_attendance = float(y[-1])
    
    # Trend Analysis
    trend_slope = calculate_trend(y)
    trend_direction = get_trend_direction(trend_slope)
    
    # Future Prediction
    future_predictions, _ = predict_future_attendance(y, periods_ahead)
    predicted_attendance = future_predictions[-1]
    
    # Risk Classification
    risk_level, risk_score = classify_risk(
        current_attendance, 
        predicted_attendance, 
        trend_slope, 
        threshold
    )
    
    # Return clearly structured dictionary
    return {
        "current_attendance": round(current_attendance, 2),
        "trend_slope": round(trend_slope, 2),
        "trend_direction": trend_direction,
        "predicted_attendance": round(predicted_attendance, 2),
        "risk_score": risk_score,
        "risk_level": risk_level
    }


# ==================================================
# 8. ANALYZE ALL STUDENTS
# ==================================================
def analyze_all_students(df, periods_ahead=PREDICTION_PERIODS, threshold=ATTENDANCE_THRESHOLD):
    """
    Analyzes attendance for every unique student-subject combination.
    """
    results = []
    
    # Group by student_id and subject
    grouped = df.groupby(['student_id', 'subject'])
    
    for (student, subject), group in grouped:
        # Sort attendance chronologically
        group = group.sort_values(by='week')
        history = group['attendance_percentage'].tolist()
        
        name = group['name'].iloc[0] if 'name' in group.columns else "Unknown"
        section = group['section'].iloc[0] if 'section' in group.columns else "Unknown"
        branch = group['branch'].iloc[0] if 'branch' in group.columns else "Unknown"
        semester = group['semester'].iloc[0] if 'semester' in group.columns else "Unknown"
        
        try:
            # Analyze each student-subject combination
            analysis = analyze_student_attendance(history, periods_ahead, threshold)
            
            # Store results
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
            pass
            
    return pd.DataFrame(results)


# ==================================================
# 9. EARLY WARNING FILTER
# ==================================================
def extract_early_warnings(results_df, threshold=ATTENDANCE_THRESHOLD):
    """
    Extracts proactive early warnings where:
    current attendance >= 75 AND predicted attendance < 75
    """
    return results_df[
        (results_df['current_attendance'] >= threshold) & 
        (results_df['predicted_attendance'] < threshold)
    ]


# ==================================================
# 10. MAIN EXECUTION PIPELINE
# ==================================================
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(base_dir, "data", "attendance_dataset.csv.xls")
    output_csv = os.path.join(base_dir, "prediction_results.csv")
    early_warning_csv = os.path.join(base_dir, "early_warning_students.csv")
    
    if os.path.exists(input_csv):
        print("========================================")
        print("1. Loading Dataset")
        print("========================================")
        df = load_attendance_data(input_csv)
        print(f"Loaded {len(df)} records.\n")
        
        print("========================================")
        print("2. Analyzing Students")
        print("========================================")
        results_df = analyze_all_students(df)
        print(f"Analyzed {len(results_df)} student-subject combinations.\n")
        
        print("========================================")
        print("3. Sorting Results")
        print("========================================")
        results_df = results_df.sort_values(by='risk_score', ascending=False).reset_index(drop=True)
        print("Sorted by highest risk.\n")
        
        print("========================================")
        print("4. Creating Early Warning List")
        print("========================================")
        early_warning_df = extract_early_warnings(results_df)
        print(f"Found {len(early_warning_df)} early warning cases.\n")
        
        print("========================================")
        print("5. Saving Results")
        print("========================================")
        results_df.to_csv(output_csv, index=False)
        early_warning_df.to_csv(early_warning_csv, index=False)
        print(f"Saved: {os.path.basename(output_csv)}")
        print(f"Saved: {os.path.basename(early_warning_csv)}\n")
        
        print("========================================")
        print("6. Summary")
        print("========================================")
        high_count = len(results_df[results_df['risk_level'] == 'HIGH'])
        medium_count = len(results_df[results_df['risk_level'] == 'MEDIUM'])
        low_count = len(results_df[results_df['risk_level'] == 'LOW'])
        
        print(f"Total Analyzed: {len(results_df)}")
        print(f"HIGH Risk:      {high_count}")
        print(f"MEDIUM Risk:    {medium_count}")
        print(f"LOW Risk:       {low_count}")
        
    else:
        print(f"Error: Dataset not found at {input_csv}")
