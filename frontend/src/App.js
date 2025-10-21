import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [selectedFiles, setSelectedFiles] = useState([]);
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
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelect(Array.from(e.dataTransfer.files));
    }
  };

  const handleFilesSelect = (filesArray) => {
    const validExtensions = ['csv', 'xlsx', 'xls'];
    const invalidFiles = [];
    const validFiles = [];
    
    filesArray.forEach(file => {
      const fileExtension = file.name.split('.').pop().toLowerCase();
      if (validExtensions.includes(fileExtension)) {
        validFiles.push(file);
      } else {
        invalidFiles.push(file.name);
      }
    });
    
    if (invalidFiles.length > 0) {
      setMessage(`Invalid file format: ${invalidFiles.join(', ')}. Please upload CSV or Excel files only.`);
      setMessageType('error');
    } else {
      setMessage('');
      setMessageType('');
    }
    
    if (validFiles.length > 0) {
      setSelectedFiles(validFiles);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesSelect(Array.from(e.target.files));
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleProcess = async () => {
    if (selectedFiles.length === 0) {
      setMessage('Please select at least one file');
      setMessageType('error');
      return;
    }

    setIsProcessing(true);
    const fileCount = selectedFiles.length;
    setMessage(`Processing ${fileCount} file${fileCount > 1 ? 's' : ''}...`);
    setMessageType('');

    const formData = new FormData();
    
    // Append all files
    selectedFiles.forEach(file => {
      formData.append('files', file);
    });
    
    if (courseName.trim()) {
      formData.append('course_name', courseName.trim());
    }

    try {
      // Use environment variable for API URL, fallback to localhost for development
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await axios.post(`${apiUrl}/api/upload`, formData, {
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
      let filename = 'cleaned_master_data.csv';
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

      setMessage(`Successfully processed ${fileCount} file${fileCount > 1 ? 's' : ''}! Your cleaned CSV has been downloaded.`);
      setMessageType('success');
      setSelectedFiles([]);
    } catch (error) {
      let errorMessage = 'An error occurred while processing the files.';
      
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
                Drag and drop your files here
              </p>
              <p className="drop-zone-subtext">or</p>
              <label className="file-input-label">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileChange}
                  className="file-input"
                  disabled={isProcessing}
                  multiple
                />
                <span className="file-input-button">Choose Files</span>
              </label>
              <p className="file-types">Supports: CSV, XLSX, XLS (multiple files allowed)</p>
            </div>
          </div>

          {selectedFiles.length > 0 && (
            <div className="selected-files">
              <p className="selected-files-label">
                Selected files ({selectedFiles.length}):
              </p>
              <ul className="files-list">
                {selectedFiles.map((file, index) => (
                  <li key={index} className="file-item">
                    <span className="file-item-name">{file.name}</span>
                    <button
                      className="remove-file-button"
                      onClick={() => removeFile(index)}
                      disabled={isProcessing}
                      aria-label={`Remove ${file.name}`}
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
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
          disabled={selectedFiles.length === 0 || isProcessing}
        >
          {isProcessing ? 'Processing...' : `Process ${selectedFiles.length > 0 ? selectedFiles.length : ''} File${selectedFiles.length !== 1 ? 's' : ''}`}
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
