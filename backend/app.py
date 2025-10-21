from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
# Allow CORS for all origins (you can restrict this later to your frontend domain)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_semester(date_str):
    """Convert date string to semester format."""
    try:
        # Parse date in format like "8/27/2025 10:13:40 AM"
        date = pd.to_datetime(date_str)
        month = date.month
        year = date.year
        
        if 1 <= month <= 6:
            return f"Spring {year}"
        elif month == 7:
            return f"Summer {year}"
        else:  # 8-12
            return f"Fall {year}"
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
        return None

def get_pre_post(date_str, semester):
    """Determine Pre/Post based on date and semester."""
    try:
        date = pd.to_datetime(date_str)
        month = date.month
        
        # Fall (Aug-Dec)
        if "Fall" in semester:
            if month in [8, 9, 10]:  # Aug-Sep-Oct = Pre
                return "Pre"
            else:  # Nov-Dec = Post
                return "Post"
        
        # Spring (Jan-Jun)
        elif "Spring" in semester:
            if month in [1, 2, 3]:  # Jan-Feb-Mar = Pre
                return "Pre"
            else:  # Apr-Jun = Post
                return "Post"
        
        # Summer (Jul)
        elif "Summer" in semester:
            if month in [6, 7]:  # Jun-Jul = Pre
                return "Pre"
            else:  # Aug-Sep = Post
                return "Post"
        
        return None
    except Exception as e:
        print(f"Error determining Pre/Post for {date_str}: {e}")
        return None

def process_single_file(file_path):
    """Process a single file with all transformations and return the dataframe."""
    try:
        # Read file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Transformation 1: Remove column "AE"
        if 'AE' in df.columns:
            df = df.drop(columns=['AE'])
        
        # Transformation 1b: Remove column "Q13 and 14" if it exists
        if 'Q13 and 14' in df.columns:
            df = df.drop(columns=['Q13 and 14'])
        
        # Transformation 2: Move column "Q35" to first position
        if 'Q35' in df.columns:
            cols = df.columns.tolist()
            cols.remove('Q35')
            cols.insert(0, 'Q35')
            df = df[cols]
        
        # Transformation 3: Rename "Q34" to "Attention Check"
        if 'Q34' in df.columns:
            df = df.rename(columns={'Q34': 'Attention Check'})
        
        # Transformation 4: Rename Q1-Q25 with " - Exam" suffix
        rename_dict = {}
        for i in range(1, 26):
            col_name = f'Q{i}'
            if col_name in df.columns:
                rename_dict[col_name] = f'{col_name} - Exam'
        df = df.rename(columns=rename_dict)
        
        # Transformation 5: Rename Q26-Q32 with " - Survey" suffix
        rename_dict = {}
        for i in range(26, 33):
            col_name = f'Q{i}'
            if col_name in df.columns:
                rename_dict[col_name] = f'{col_name} - Survey'
        df = df.rename(columns=rename_dict)
        
        # Transformation 6: Rename Q33-Q44 with " - Survey" suffix
        rename_dict = {}
        for i in range(33, 45):
            col_name = f'Q{i}'
            if col_name in df.columns:
                rename_dict[col_name] = f'{col_name} - Survey'
        df = df.rename(columns=rename_dict)
        
        # Transformation 7: Create "Semester" column based on "StartDate"
        if 'StartDate' in df.columns:
            df['Semester'] = df['StartDate'].apply(get_semester)
        else:
            raise ValueError("Required column 'StartDate' not found in file")
        
        # Transformation 8: Create "Pre/Post" column as last column
        if 'StartDate' in df.columns and 'Semester' in df.columns:
            df['Pre/Post'] = df.apply(lambda row: get_pre_post(row['StartDate'], row['Semester']), axis=1)
        
        return df
    
    except Exception as e:
        raise Exception(f"Error processing file: {str(e)}")

def process_files(file_paths, course_name=None):
    """Process multiple files, combine them, and return the output path."""
    try:
        processed_dfs = []
        
        # Process each file
        for file_path in file_paths:
            df = process_single_file(file_path)
            processed_dfs.append(df)
        
        # Combine all dataframes
        if len(processed_dfs) == 1:
            combined_df = processed_dfs[0]
        else:
            # Concatenate all dataframes, keeping all columns
            combined_df = pd.concat(processed_dfs, ignore_index=True, sort=False)
        
        # Transformation 9: Add "Course Name" column if course name provided
        if course_name:
            combined_df['Course Name'] = course_name
        
        # Save to CSV
        if course_name:
            output_filename = f"{course_name}.csv"
        else:
            output_filename = "cleaned_master_data.csv"
        
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        combined_df.to_csv(output_path, index=False, encoding='utf-8')
        
        return output_path, output_filename
    
    except Exception as e:
        raise Exception(f"Error processing files: {str(e)}")

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        # Check if files are present (support both single 'file' and multiple 'files')
        files_to_process = []
        
        # Check for multiple files
        if 'files' in request.files:
            files_list = request.files.getlist('files')
            if not files_list or all(f.filename == '' for f in files_list):
                return jsonify({'error': 'No files selected'}), 400
            files_to_process = files_list
        # Check for single file (backward compatibility)
        elif 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            files_to_process = [file]
        else:
            return jsonify({'error': 'No files provided'}), 400
        
        # Validate all files
        for file in files_to_process:
            if not allowed_file(file.filename):
                return jsonify({'error': f'Invalid file format: {file.filename}. Please upload CSV or Excel files only.'}), 400
        
        # Get course name from form data
        course_name = request.form.get('course_name', '').strip()
        
        # Save all uploaded files
        saved_filepaths = []
        try:
            for file in files_to_process:
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                saved_filepaths.append(filepath)
            
            # Process all files and combine them
            output_path, output_filename = process_files(saved_filepaths, course_name if course_name else None)
            
            # Clean up uploaded files
            for filepath in saved_filepaths:
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            # Send cleaned file
            return send_file(
                output_path,
                as_attachment=True,
                download_name=output_filename,
                mimetype='text/csv'
            )
        except Exception as e:
            # Clean up uploaded files in case of error
            for filepath in saved_filepaths:
                if os.path.exists(filepath):
                    os.remove(filepath)
            raise e
    
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)
