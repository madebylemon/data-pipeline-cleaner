import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState(''); // 'success' or 'error'
  const [dragActive, setDragActive] = useState(false);
  const [courseName, setCourseName] = useState('');

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (file) => {
    const validExtensions = ['csv', 'xlsx', 'xls'];
    const fileExtension = file.name.split('.').pop().toLowerCase();
    
    if (validExtensions.includes(fileExtension)) {
      setSelectedFile(file);
      setMessage('');
      setMessageType('');
    } else {
      setMessage('Invalid file format. Please upload CSV or Excel files only.');
      setMessageType('error');
      setSelectedFile(null);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleProcess = async () => {
    if (!selectedFile) {
      setMessage('Please select a file first');
      setMessageType('error');
      return;
    }

    setIsProcessing(true);
    setMessage('Processing your file...');
    setMessageType('');

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (courseName.trim()) {
      formData.append('course_name', courseName.trim());
    }

    try {
      const response = await axios.post('http://localhost:5001/api/upload', formData, {
        responseType: 'blob',
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Get filename from content-disposition header or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `cleaned_${selectedFile.name.split('.')[0]}.csv`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);

      setMessage('File processed successfully! Your cleaned CSV has been downloaded.');
      setMessageType('success');
      setSelectedFile(null);
    } catch (error) {
      let errorMessage = 'An error occurred while processing the file.';
      
      if (error.response && error.response.data) {
        // Try to parse error message from blob
        try {
          const text = await error.response.data.text();
          const errorData = JSON.parse(text);
          errorMessage = errorData.error || errorMessage;
        } catch (e) {
          // If parsing fails, use default message
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setMessage(errorMessage);
      setMessageType('error');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="App">
      <header className="header">
        <h1>Data Pipeline Cleaner</h1>
        <p>Clean and transform your CSV/Excel files</p>
      </header>

      <main className="main-content">
        <div className="upload-section">
          <div
            className={`drop-zone ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <div className="drop-zone-content">
              <svg 
                width="64" 
                height="64" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <p className="drop-zone-text">
                Drag and drop your file here
              </p>
              <p className="drop-zone-subtext">or</p>
              <label className="file-input-label">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileChange}
                  className="file-input"
                  disabled={isProcessing}
                />
                <span className="file-input-button">Choose File</span>
              </label>
              <p className="file-types">Supports: CSV, XLSX, XLS</p>
            </div>
          </div>

          {selectedFile && (
            <div className="selected-file">
              <p className="selected-file-label">Selected file:</p>
              <p className="selected-file-name">{selectedFile.name}</p>
            </div>
          )}
        </div>

        <div className="course-name-section">
          <input
            type="text"
            className="course-name-input"
            placeholder="Enter course name (optional)"
            value={courseName}
            onChange={(e) => setCourseName(e.target.value)}
            disabled={isProcessing}
          />
          <p className="course-name-hint">e.g., PSY101_Fall2025</p>
        </div>

        <button
          className="process-button"
          onClick={handleProcess}
          disabled={!selectedFile || isProcessing}
        >
          {isProcessing ? 'Processing...' : 'Process File'}
        </button>

        {message && (
          <div className={`message ${messageType}`}>
            {message}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
