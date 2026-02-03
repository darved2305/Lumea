import { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Eye,
  Download,
  RefreshCw,
  Trash2,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Clock,
  AlertCircle,
  FolderOpen,
} from 'lucide-react';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import { useWebSocket } from '../hooks/useWebSocket';
import { HealthProfileCard } from '../components/profile';
import './Reports.css';

const API_BASE = 'http://localhost:8000';

// Types
interface Report {
  id: string;
  name: string;
  category: string;
  type: string;
  date: string;
  staff?: string;
  region?: string;
  status: 'processing' | 'complete' | 'failed';
  extractedMetrics?: number;
  lastUpdated: string;
}

// Map backend status to frontend status
function mapStatus(backendStatus: string): 'processing' | 'complete' | 'failed' {
  const status = backendStatus.toLowerCase();
  if (status === 'processed' || status === 'confirmed' || status === 'extracted') {
    return 'complete';
  }
  if (status === 'failed') {
    return 'failed';
  }
  // uploaded, extracting, processing -> all map to processing
  return 'processing';
}

const categories = ['All Categories', 'Lab', 'Dental', 'MRI', 'X-ray', 'Prescription', 'Sleep'];
const documentTypes = ['All Types', 'Blood Panel', 'Lipid Panel', 'Checkup', 'Brain Scan', 'Chest'];

// WebSocket event data types
interface ReportParsedData {
  report_id?: string;
  status?: string;
  extracted_metrics_count?: number;
}

interface ProcessingStartedData {
  report_id?: string;
}

function Reports() {
  const [reports, setReports] = useState<Report[]>([]);
  const [_loading, setLoading] = useState(true); // prefixed with _ to avoid unused warning
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All Categories');
  const [selectedType, setSelectedType] = useState('All Types');
  const [selectedDate, setSelectedDate] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedReports, setSelectedReports] = useState<Set<string>>(new Set());
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const itemsPerPage = 5;

  // WebSocket for real-time updates
  useWebSocket({
    onReportsListUpdated: useCallback(() => {
      console.log('WS: Reports list updated, refetching...');
      fetchReports();
    }, []),
    onReportParsed: useCallback((data: ReportParsedData) => {
      console.log('WS: Report parsed', data);
      // Update report status in local state immediately
      if (data.report_id) {
        setReports(prev => prev.map(r =>
          r.id === data.report_id
            ? { ...r, status: data.status === 'complete' ? 'complete' : 'failed', extractedMetrics: data.extracted_metrics_count }
            : r
        ));
      }
      // Also refetch to ensure consistency
      fetchReports();
    }, []),
    onReportProcessingStarted: useCallback((_data: ProcessingStartedData) => {
      console.log('WS: Report processing started', _data);
    }, []),
    onProfileUpdated: useCallback(() => {
      console.log('WS: Profile updated');
      // The HealthProfileCard handles its own refresh
    }, []),
  });

  // Fetch reports from API
  const fetchReports = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/reports`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Fetched reports:', data);
        // Map backend response to frontend format
        const mappedReports: Report[] = data.map((r: any) => ({
          id: r.id,
          name: r.filename,
          category: r.category || 'Lab',
          type: r.file_type || 'Unknown',
          date: new Date(r.report_date || r.uploaded_at).toLocaleDateString('en-GB'),
          staff: r.staff || '-',
          region: r.region || '-',
          status: mapStatus(r.status),
          extractedMetrics: r.observation_count,
          lastUpdated: r.uploaded_at,
        }));
        setReports(mappedReports);
      } else {
        console.error('Failed to fetch reports:', response.status);
      }
    } catch (error) {
      console.error('Error fetching reports:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Filter reports
  const filteredReports = reports.filter(report => {
    const matchesSearch = report.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'All Categories' || report.category === selectedCategory;
    const matchesType = selectedType === 'All Types' || report.type === selectedType;
    return matchesSearch && matchesCategory && matchesType;
  });

  const totalPages = Math.ceil(filteredReports.length / itemsPerPage);
  const paginatedReports = filteredReports.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Handle file upload
  const handleFileUpload = useCallback(async (files: FileList) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setUploadError('Not authenticated. Please log in.');
      return;
    }

    setUploadError(null);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const reportId = `upload_${Date.now()}_${i}`;

      try {
        // Show upload progress
        setUploadProgress(prev => ({ ...prev, [reportId]: 0 }));

        // Create FormData - DO NOT set Content-Type header manually!
        const formData = new FormData();
        formData.append('file', file);
        // Optional: add date if needed
        // formData.append('report_date', new Date().toISOString());

        const xhr = new XMLHttpRequest();

        // Track upload progress
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            setUploadProgress(prev => ({ ...prev, [reportId]: percentComplete }));
          }
        };

        xhr.onload = () => {
          if (xhr.status === 200 || xhr.status === 201) {
            console.log('Upload successful:', xhr.responseText);
            // Upload complete, add a temporary row immediately
            try {
              const response = JSON.parse(xhr.responseText);
              setReports(prev => [{
                id: response.id,
                name: file.name,
                category: 'Lab',
                type: file.name.split('.').pop() || 'Unknown',
                date: new Date().toLocaleDateString('en-GB'),
                staff: '-',
                region: 'New Hampshire',
                status: 'processing',
                extractedMetrics: 0,
                lastUpdated: new Date().toISOString(),
              }, ...prev]);
            } catch (e) {
              // Parse error, just refetch
            }

            // Clear progress and poll for updates
            setTimeout(() => {
              setUploadProgress(prev => {
                const { [reportId]: _, ...rest } = prev;
                return rest;
              });
              fetchReports();
              // Poll every 2 seconds for 30 seconds to check processing status
              let pollCount = 0;
              const pollInterval = setInterval(() => {
                pollCount++;
                fetchReports();
                if (pollCount >= 15) {
                  clearInterval(pollInterval);
                }
              }, 2000);
            }, 1000);
          } else {
            console.error('Upload failed:', xhr.status, xhr.statusText, xhr.responseText);
            let errorMessage = 'Upload failed';
            try {
              const errData = JSON.parse(xhr.responseText);
              errorMessage = errData.detail || errorMessage;
            } catch (e) { }
            setUploadError(errorMessage);
            setUploadProgress(prev => {
              const { [reportId]: _, ...rest } = prev;
              return rest;
            });
          }
        };

        xhr.onerror = () => {
          console.error('Upload network error');
          setUploadError('Network error. Check if backend is running.');
          setUploadProgress(prev => {
            const { [reportId]: _, ...rest } = prev;
            return rest;
          });
        };

        xhr.open('POST', `${API_BASE}/api/reports/upload`);
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        // DO NOT set Content-Type - browser will set it with boundary for multipart
        xhr.send(formData);
      } catch (error) {
        console.error('Upload error:', error);
        setUploadError('Upload failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
        setUploadProgress(prev => {
          const { [reportId]: _, ...rest } = prev;
          return rest;
        });
      }
    }
  }, [fetchReports]);

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  }, [handleFileUpload]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files);
    }
  }, [handleFileUpload]);

  // Selection handlers
  const toggleSelectReport = (id: string) => {
    setSelectedReports(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedReports.size === paginatedReports.length) {
      setSelectedReports(new Set());
    } else {
      setSelectedReports(new Set(paginatedReports.map(r => r.id)));
    }
  };

  // Actions
  const handleView = async (report: Report) => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/reports/${report.id}/debug`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        alert(`Report: ${report.name}\nStatus: ${data.status}\nExtraction Method: ${data.extraction_method || 'N/A'}\nMetrics Found: ${data.extracted_metrics_count}\nText Length: ${data.text_length} chars\n\nPreview:\n${data.text_preview?.substring(0, 500) || 'No text'}`);
      }
    } catch (error) {
      console.error('Error viewing report:', error);
    }
  };

  const handleDownload = async (report: Report) => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      window.open(`${API_BASE}/api/reports/${report.id}/download?token=${token}`, '_blank');
    } catch (error) {
      console.error('Error downloading report:', error);
      alert('Download feature coming soon. File is stored at: ' + report.name);
    }
  };

  const handleReprocess = (report: Report) => {
    setReports(prev => prev.map(r =>
      r.id === report.id ? { ...r, status: 'processing' as const } : r
    ));

    // Simulate reprocessing
    setTimeout(() => {
      setReports(prev => prev.map(r =>
        r.id === report.id
          ? { ...r, status: 'complete' as const, extractedMetrics: Math.floor(Math.random() * 20) + 5 }
          : r
      ));
    }, 3000);
  };

  const handleDelete = async (report: Report) => {
    if (!confirm(`Delete "${report.name}"?`)) return;

    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/reports/${report.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setReports(prev => prev.filter(r => r.id !== report.id));
        setSelectedReports(prev => {
          const newSet = new Set(prev);
          newSet.delete(report.id);
          return newSet;
        });
      } else {
        alert('Failed to delete report');
      }
    } catch (error) {
      console.error('Error deleting report:', error);
      alert('Error deleting report');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <CheckCircle2 size={16} className="status-icon complete" />;
      case 'processing':
        return <Clock size={16} className="status-icon processing" />;
      case 'failed':
        return <AlertCircle size={16} className="status-icon failed" />;
      default:
        return null;
    }
  };

  return (
    <div className="reports-page">
      <DashboardNavbar userName="User" userStatus="" />

      <div className="reports-content">
        <div className="reports-container">
          {/* Header */}
          <div className="reports-header">
            <div className="reports-title-section">
              <h1>Document Details</h1>
              <p>Upload and manage your health reports. All documents are processed securely.</p>
            </div>
            <div className="reports-header-actions">
              <button className="btn-secondary">Open Documentation</button>
              <button className="btn-secondary">Setup Details</button>
            </div>
          </div>

          {/* Upload Error */}
          {uploadError && (
            <div className="upload-error">
              <AlertCircle size={16} />
              {uploadError}
              <button onClick={() => setUploadError(null)}>×</button>
            </div>
          )}

          {/* Tabs */}
          <div className="reports-tabs">
            <button className="tab-btn active">Overview</button>
          </div>

          {/* Search and Filters */}
          <div className="reports-toolbar">
            <div className="search-container">
              <Search size={18} className="search-icon" />
              <input
                type="text"
                placeholder="Search for document"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
            </div>
          </div>

          {/* Filter Row */}
          <div className="filter-row">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="filter-select"
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>

            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="filter-select"
            >
              {documentTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>

            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="filter-select"
              placeholder="Document Date"
            />
          </div>

          {/* Upload and Profile Section - 2 Column Layout */}
          <div className="upload-profile-grid">
            {/* Left: Upload Dropzone */}
            <div
              className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileInputChange}
                accept=".pdf,.png,.jpg,.jpeg"
                multiple
                hidden
              />
              <FolderOpen size={40} className="dropzone-icon" />
              <p>Drop your documents here, or <span className="browse-link">click to browse</span></p>
            </div>

            {/* Right: Health Profile Card */}
            <HealthProfileCard />
          </div>

          {/* Upload Progress */}
          <AnimatePresence>
            {Object.keys(uploadProgress).length > 0 && (
              <motion.div
                className="upload-progress-container"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                {Object.entries(uploadProgress).map(([id, progress]) => (
                  <div key={id} className="upload-progress-item">
                    <span className="progress-label">Processing...</span>
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <span className="progress-percent">{Math.round(progress)}%</span>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Reports Table */}
          <div className="reports-table-container">
            <table className="reports-table">
              <thead>
                <tr>
                  <th className="checkbox-col">
                    <input
                      type="checkbox"
                      checked={selectedReports.size === paginatedReports.length && paginatedReports.length > 0}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th>Document Name ▼</th>
                  <th>Document Type</th>
                  <th>Document Date</th>
                  <th>Status ▼</th>
                  <th className="operations-col">Operations</th>
                </tr>
              </thead>
              <tbody>
                {paginatedReports.map((report) => (
                  <motion.tr
                    key={report.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className={selectedReports.has(report.id) ? 'selected' : ''}
                  >
                    <td className="checkbox-col">
                      <input
                        type="checkbox"
                        checked={selectedReports.has(report.id)}
                        onChange={() => toggleSelectReport(report.id)}
                      />
                    </td>
                    <td className="doc-name">
                      <span className={selectedReports.has(report.id) ? 'highlighted' : ''}>
                        {report.name}
                      </span>
                    </td>
                    <td>
                      <span className="doc-type-badge">{report.category}</span>
                    </td>
                    <td>{report.date}</td>
                    <td>
                      <span className={`status-badge ${report.status}`}>
                        {getStatusIcon(report.status)}
                        {report.status.charAt(0).toUpperCase() + report.status.slice(1)}
                      </span>
                    </td>
                    <td className="actions-cell operations-col">
                      <button
                        className="action-btn"
                        onClick={() => handleView(report)}
                        title="View"
                      >
                        <Eye size={16} />
                      </button>
                      <button
                        className="action-btn"
                        onClick={() => handleReprocess(report)}
                        title="Reprocess OCR"
                        disabled={report.status === 'processing'}
                      >
                        <RefreshCw size={16} className={report.status === 'processing' ? 'spinning' : ''} />
                      </button>
                      <button
                        className="action-btn"
                        onClick={() => handleDelete(report)}
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                      <button
                        className="action-btn"
                        onClick={() => handleDownload(report)}
                        title="Download"
                      >
                        <Download size={16} />
                      </button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="reports-pagination">
            <span className="pagination-info">
              {(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, filteredReports.length)} of {filteredReports.length} pages
            </span>
            <div className="pagination-controls">
              <span>You're on page</span>
              <select
                value={currentPage}
                onChange={(e) => setCurrentPage(Number(e.target.value))}
                className="page-select"
              >
                {Array.from({ length: totalPages }, (_, i) => (
                  <option key={i + 1} value={i + 1}>{i + 1}</option>
                ))}
              </select>
              <button
                className="pagination-btn"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft size={18} />
              </button>
              <button
                className="pagination-btn"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Reports;
