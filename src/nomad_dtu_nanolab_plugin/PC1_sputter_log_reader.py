import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog

# Function to select the file
def select_file():
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    path_to_github = filedialog.askopenfilename()
    print(f"Selected file: {path_to_github}")
    return path_to_github

# Function to process the file and create the dictionary
def process_file(path_to_github):
    try:
        # Read the CSV file with error handling for irregular rows
        df = pd.read_csv(path_to_github, delimiter=',', header=None, on_bad_lines='skip')
        print(f"Raw data from the CSV (first 10 rows):\n{df.head(10)}")

        # Drop empty rows
        df = df.dropna(how='all')

        # Check if the 4th row exists
        if len(df) > 3:
            headers = df.iloc[3].dropna().tolist()  # Extract headers from the 4th row
            print(f"Headers found in the CSV: {headers}")

            # Create a dictionary with abbreviations
            header_to_abbreviation = {
                header: header.replace("PC1", "").strip().replace(" ", "_").lower()
                for header in headers
            }

            print("Generated dictionary mapping headers to abbreviations:")
            print(header_to_abbreviation)

            # Use the dictionary further in your code as needed
            return header_to_abbreviation
        else:
            print("The CSV file does not have enough rows to extract headers.")
            return None

    except Exception as e:
        print(f"Error processing file: {e}")
        return None

# Select the file
path_to_github = select_file()

# Process the file and create the dictionary
header_to_abbreviation = process_file(path_to_github)