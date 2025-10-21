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

def extract_metadata_from_filename(filename):
    """
    Extract metadata from filename dynamically.
    Example: "EMCS+Group+-+1501+-+Section+3+-+sp2024+-+Post_June+13,+2025_06.14.csv"
    Returns: {'course_name': '1501', 'semester': 'sp2024', 'pre_post': 'Post'}
    """
    import re
    
    # Remove file extension
    name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
    
    # Replace common separators with spaces for easier parsing
    normalized = name_without_ext.replace('+', ' ').replace('-', ' ').replace('_', ' ')
    
    metadata = {
        'course_name': None,
        'semester': None,
        'pre_post': None
    }
    
    # Extract Course Name (look for 4-digit number, or alphanumeric course code)
    course_match = re.search(r'\b(\d{4})\b', normalized)
    if course_match:
        metadata['course_name'] = course_match.group(1)
    
    # Extract Semester (pattern like sp2024, fa2024, fall2024, spring2025, etc.)
    semester_match = re.search(r'\b(sp|fa|su|spring|fall|summer)\s*(\d{4})\b', normalized, re.IGNORECASE)
    if semester_match:
        term = semester_match.group(1).lower()
        year = semester_match.group(2)
        # Normalize to short format
        if term.startswith('sp'):
            metadata['semester'] = f"sp{year}"
        elif term.startswith('fa'):
            metadata['semester'] = f"fa{year}"
        elif term.startswith('su'):
            metadata['semester'] = f"su{year}"
    
    # Extract Pre/Post (look for the word "Pre" or "Post" before a date or underscore)
    pre_post_match = re.search(r'\b(Pre|Post)\b', normalized, re.IGNORECASE)
    if pre_post_match:
        metadata['pre_post'] = pre_post_match.group(1).capitalize()
    
    return metadata

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

def process_single_file(file_path, original_filename):
    """Process a single file with all transformations and return the dataframe."""
    try:
        # Extract metadata from filename
        metadata = extract_metadata_from_filename(original_filename)
        
        # Read file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Transformation 0: Delete rows 2 and 3 (indices 0 and 1) across ALL columns
        # This removes the first two data rows after the header
        if len(df) > 2:
            df = df.drop([0, 1]).reset_index(drop=True)
        elif len(df) > 0:
            # If there are only 1-2 rows, drop what exists
            df = df.drop(df.index[0:min(2, len(df))]).reset_index(drop=True)
        
        # Transformation 1: Remove specific metadata columns (not by position, by name)
        # These are the typical Qualtrics metadata columns to remove
        metadata_cols_to_remove = [
            'StartDate', 'EndDate', 'Status', 'IPAddress', 'Progress', 
            'Duration (in seconds)', 'Finished', 'RecordedDate', 'ResponseId',
            'RecipientLastName', 'RecipientFirstName', 'RecipientEmail',
            'ExternalReference', 'LocationLatitude', 'LocationLongitude',
            'DistributionChannel', 'UserLanguage'
        ]
        cols_to_drop = [col for col in metadata_cols_to_remove if col in df.columns]
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop, errors='ignore')
        
        # Transformation 1b: Remove column "AE"
        if 'AE' in df.columns:
            df = df.drop(columns=['AE'])
        
        # Transformation 1c: Remove column "Q13 and 14" if it exists
        if 'Q13 and 14' in df.columns:
            df = df.drop(columns=['Q13 and 14'])
        
        # Transformation 2: Rename "Q34" to "Attention Check"
        if 'Q34' in df.columns:
            df = df.rename(columns={'Q34': 'Attention Check'})
        
        # Transformation 3: Find and rename Q35 (any variation) to ID, then move to first position
        # Check for Q35 with any variation
        q35_col = None
        for col in df.columns:
            if col == 'Q35' or col.startswith('Q35'):
                q35_col = col
                break
        
        if q35_col:
            # Rename to ID
            df = df.rename(columns={q35_col: 'ID'})
            # Move ID to first position
            cols = df.columns.tolist()
            cols.remove('ID')
            cols.insert(0, 'ID')
            df = df[cols]
        
        # Transformation 4: Remove ALL survey-related columns (Q26-Q44 with ANY suffix)
        # This catches Q26, Q26_TEXT, Q33_4_TEXT, Q43_8_TEXT, etc.
        import re
        cols_to_remove = []
        for col in df.columns:
            col_str = str(col).upper()
            # Check if column contains Q26 through Q44 in ANY position
            for i in range(26, 45):
                # Match Q{i} followed by any character or end of string
                # This catches: Q26, Q26_TEXT, Q26_1_TEXT, Q26-anything, etc.
                # But NOT Q260 (3-digit number)
                pattern = rf'Q{i}(?:_|\s|-|$|[^\d])'
                if re.search(pattern, col_str):
                    cols_to_remove.append(col)
                    break
        
        if cols_to_remove:
            df = df.drop(columns=cols_to_remove, errors='ignore')
        
        # Transformation 5: Also remove any columns with "Survey" in the name (extra safety)
        survey_cols = [col for col in df.columns if 'survey' in str(col).lower()]
        if survey_cols:
            df = df.drop(columns=survey_cols, errors='ignore')
        
        # Transformation 7: Add metadata columns from filename
        # Add Course Name column
        if metadata['course_name']:
            df['Course Name'] = metadata['course_name']
        
        # Add Semester column from filename (overrides date-based semester if present)
        if metadata['semester']:
            df['Semester'] = metadata['semester']
        elif 'StartDate' in df.columns:
            # Fallback to date-based semester if filename doesn't have it
            df['Semester'] = df['StartDate'].apply(get_semester)
        
        # Add Pre/Post column from filename (overrides date-based pre/post if present)
        if metadata['pre_post']:
            df['Pre/Post'] = metadata['pre_post']
        elif 'StartDate' in df.columns and 'Semester' in df.columns:
            # Fallback to date-based pre/post if filename doesn't have it
            df['Pre/Post'] = df.apply(lambda row: get_pre_post(row['StartDate'], row['Semester']), axis=1)
        
        return df
    
    except Exception as e:
        raise Exception(f"Error processing file: {str(e)}")

def process_files(file_info_list):
    """
    Process multiple files, combine them, and return the output path.
    file_info_list: List of tuples (file_path, original_filename)
    """
    try:
        processed_dfs = []
        
        # Process each file with its original filename
        for file_path, original_filename in file_info_list:
            df = process_single_file(file_path, original_filename)
            processed_dfs.append(df)
        
        # Combine all dataframes
        if len(processed_dfs) == 1:
            combined_df = processed_dfs[0]
        else:
            # Concatenate all dataframes, keeping all columns
            combined_df = pd.concat(processed_dfs, ignore_index=True, sort=False)
        
        # Generate output filename - always use default name
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
        
        # Save all uploaded files and track original filenames
        file_info_list = []
        try:
            for file in files_to_process:
                original_filename = file.filename  # Keep original filename before securing
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                file_info_list.append((filepath, original_filename))
            
            # Process all files and combine them (passing original filenames)
            output_path, output_filename = process_files(file_info_list)
            
            # Clean up uploaded files
            for filepath, _ in file_info_list:
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
            for filepath, _ in file_info_list:
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
