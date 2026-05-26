import pandas as pd
import sys

def check_null_values(csv_file_path):
    try:
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv('coursera_course_dataset_v3.csv')
        
        # Get the sum of null values for each column
        null_counts = df.isnull().sum()
        # Filter to keep only columns that actually have null values (> 0)
        columns_with_nulls = null_counts[null_counts > 0]
        
        # Check if there are any null values at all
        if columns_with_nulls.empty:
            print("Great news! There are no null values in this CSV file.")
        else:
            print(f"Found missing values in {len(columns_with_nulls)} column(s):\n")
            
            # Print the column names and their exact null count
            for column_name, null_count in columns_with_nulls.items():
                print(f"Column: '{column_name}' -> Total Null Values: {null_count}")
                
    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found. Please check the path.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Example Usage ---
if __name__ == "__main__":
    # Replace 'your_data.csv' with the actual path to your CSV file
    file_path = 'your_data.csv' 
    check_null_values(file_path)