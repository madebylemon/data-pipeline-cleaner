# Data Pipeline Cleaner

A full-stack application for cleaning and transforming CSV/Excel files with automated data processing rules.

## Features

- Upload CSV or Excel files (.csv, .xlsx, .xls)
- Automatic data transformations including:
  - Column removal and reordering
  - Column renaming with custom suffixes
  - Date-based semester and pre/post classification
- Clean, minimalist black and white UI
- Drag-and-drop file upload
- Automatic download of cleaned CSV files

## Project Structure

```
Pipeline/
├── backend/          # Python Flask API
│   ├── app.py
│   └── requirements.txt
└── frontend/         # React application
    ├── public/
    ├── src/
    └── package.json
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the Flask server:
```bash
python app.py
```

The backend will run on `http://localhost:5000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will run on `http://localhost:3000`

## Usage

1. Start both the backend and frontend servers
2. Open your browser to `http://localhost:3000`
3. Upload a CSV or Excel file using drag-and-drop or the file picker
4. Click "Process File"
5. The cleaned CSV will automatically download

## Data Transformations

The application performs the following transformations in order:

1. **Remove column "AE"** entirely
2. **Move column "Q35"** to the first position
3. **Rename column "Q34"** to "Attention Check"
4. **Rename Q1-Q25**: Add " - Exam" suffix
5. **Rename Q33-Q44**: Add " - Survey" suffix
6. **Create "Semester" column** based on StartDate:
   - Jan-Jun: Spring [YEAR]
   - Jul: Summer [YEAR]
   - Aug-Dec: Fall [YEAR]
7. **Create "Pre/Post" column** (last column) based on date ranges:
   - Fall: Aug-Oct = Pre, Nov-Dec = Post
   - Spring: Jan-Mar = Pre, Apr-Jun = Post
   - Summer: Jun-Jul = Pre, Aug-Sep = Post

## Requirements

### Backend
- Python 3.8+
- Flask 3.0.0
- pandas 2.1.4
- openpyxl 3.1.2

### Frontend
- Node.js 14+
- React 18.2.0
- axios 1.6.2

## Error Handling

- Validates file formats before processing
- Handles missing required columns with clear error messages
- Displays user-friendly error messages in the UI
- Proper date parsing error handling

## License

MIT
