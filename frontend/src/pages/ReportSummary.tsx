import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Filter,
  FileText,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Calendar,
  Loader2,
  X,
  Check,
  AlertCircle,
  Maximize2,
  Grid,
} from 'lucide-react';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import './ReportSummary.css';

const API_BASE = 'http://localhost:8000';

// Types
interface Report {
  id: string;
  filename: string;
  category: string | null;
  doc_type: string | null;
  report_date: string | null;
  uploaded_at: string;
  file_path: string;
  file_type: string;
  preview_url: string;
}

interface SummaryHighlights {
  positive: string[];
  needs_attention: string[];
  next_steps: string[];
}

interface KeyFinding {
  item: string;
  evidence: string;
}

interface SummaryJSON {
  title: string;
  highlights: SummaryHighlights;
  plain_language_summary: string;
  key_findings: KeyFinding[];
  confidence: number;
}

interface KeyDifference {
  metric: string;
  from: string;
  to: string;
  evidence: string;
}

interface ComparisonJSON {
  title: string;
  overall_change: string;
  improvements: string[];
  worsened: string[];
  stable: string[];
  key_differences: KeyDifference[];
  next_steps: string[];
  confidence: number;
}

interface CategoryInfo {
  name: string;
  count: number;
}

// Toast notification state
interface Toast {
  id: string;
  message: string;
  type: 'error' | 'warning' | 'success';
}

function ReportSummary() {
  // State
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [docTypes, setDocTypes] = useState<CategoryInfo[]>([]);
  
  // AI Results
  const [summaryResult, setSummaryResult] = useState<{
    data: SummaryJSON | null;
    cached: boolean;
    generatedAt: Date | null;
    modelName: string;
    loading: boolean;
    error: string | null;
  }>({
    data: null,
    cached: false,
    generatedAt: null,
    modelName: '',
    loading: false,
    error: null,
  });
  
  const [comparisonResult, setComparisonResult] = useState<{
    data: ComparisonJSON | null;
    cached: boolean;
    generatedAt: Date | null;
    modelName: string;
    loading: boolean;
    error: string | null;
  }>({
    data: null,
    cached: false,
    generatedAt: null,
    modelName: '',
    loading: false,
    error: null,
  });
  
  // UI state
  const [activeTab, setActiveTab] = useState<'summary' | 'comparison' | 'metrics'>('summary');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [focusedPreviewId, setFocusedPreviewId] = useState<string | null>(null);

  // Helper: Show toast
  const showToast = useCallback((message: string, type: 'error' | 'warning' | 'success' = 'error') => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  // Fetch reports
  const fetchReports = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (categoryFilter) params.append('category', categoryFilter);
      if (docTypeFilter) params.append('doc_type', docTypeFilter);
      
      const response = await fetch(`${API_BASE}/api/ai/reports-for-summary?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setReports(data);
      } else {
        console.error('Failed to fetch reports:', response.status);
        showToast('Failed to load reports');
      }
    } catch (error) {
      console.error('Error fetching reports:', error);
      showToast('Network error loading reports');
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, docTypeFilter, showToast]);

  // Fetch categories
  const fetchCategories = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/ai/categories`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories || []);
        setDocTypes(data.doc_types || []);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  }, []);

  useEffect(() => {
    fetchReports();
    fetchCategories();
  }, [fetchReports, fetchCategories]);

  // Filter reports
  const filteredReports = reports.filter(report => {
    const matchesSearch = report.filename.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  // Selected reports
  const selectedReports = filteredReports.filter(r => selectedIds.has(r.id));

  // Validate selection for comparison
  const validateSelection = useCallback((): { valid: boolean; error?: string } => {
    if (selectedIds.size < 2) {
      return { valid: true }; // Not enough for comparison, but valid for single
    }
    if (selectedIds.size > 6) {
      return { valid: false, error: 'Maximum 6 reports allowed for comparison' };
    }

    const selected = filteredReports.filter(r => selectedIds.has(r.id));
    const categories = new Set(selected.map(r => r.category).filter(Boolean));
    const docTypes = new Set(selected.map(r => r.doc_type).filter(Boolean));

    if (categories.size > 1 && docTypes.size > 1) {
      return { valid: false, error: 'Please select reports of the same type for comparison' };
    }

    return { valid: true };
  }, [selectedIds, filteredReports]);

  // Toggle selection
  const toggleSelection = useCallback((id: string) => {
    const report = filteredReports.find(r => r.id === id);
    if (!report) return;

    setSelectedIds(prev => {
      const newSet = new Set(prev);
      
      if (newSet.has(id)) {
        newSet.delete(id);
        // Clear results when deselecting
        if (newSet.size === 0) {
          setSummaryResult(prev => ({ ...prev, data: null, error: null }));
          setComparisonResult(prev => ({ ...prev, data: null, error: null }));
        }
        return newSet;
      }

      // Check max selection
      if (newSet.size >= 6) {
        showToast('Maximum 6 reports can be selected', 'warning');
        return prev;
      }

      // Check type compatibility for comparison
      if (newSet.size >= 1) {
        const existingSelected = filteredReports.filter(r => newSet.has(r.id));
        const existingCategory = existingSelected[0]?.category;
        const existingDocType = existingSelected[0]?.doc_type;
        
        if (
          report.category !== existingCategory && 
          report.doc_type !== existingDocType &&
          existingCategory && existingDocType
        ) {
          showToast('Please select reports of the same type for comparison', 'warning');
          return prev;
        }
      }

      newSet.add(id);
      return newSet;
    });
  }, [filteredReports, showToast]);

  // Generate summary
  const generateSummary = useCallback(async (forceRegenerate = false) => {
    if (selectedIds.size !== 1) return;
    
    const reportId = Array.from(selectedIds)[0];
    const token = localStorage.getItem('access_token');
    if (!token) return;

    setSummaryResult(prev => ({ ...prev, loading: true, error: null }));
    setActiveTab('summary');

    try {
      const response = await fetch(`${API_BASE}/api/ai/report-summary`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          report_id: reportId,
          force_regenerate: forceRegenerate,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate summary');
      }

      const data = await response.json();
      setSummaryResult({
        data: data.summary_json,
        cached: data.cached,
        generatedAt: new Date(data.generated_at),
        modelName: data.model_name,
        loading: false,
        error: null,
      });
    } catch (error) {
      console.error('Error generating summary:', error);
      setSummaryResult(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to generate summary',
      }));
      showToast(error instanceof Error ? error.message : 'Failed to generate summary');
    }
  }, [selectedIds, showToast]);

  // Generate comparison
  const generateComparison = useCallback(async (forceRegenerate = false) => {
    if (selectedIds.size < 2) return;
    
    const validation = validateSelection();
    if (!validation.valid) {
      showToast(validation.error || 'Invalid selection', 'error');
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) return;

    setComparisonResult(prev => ({ ...prev, loading: true, error: null }));
    setActiveTab('comparison');

    try {
      const response = await fetch(`${API_BASE}/api/ai/report-compare`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          report_ids: Array.from(selectedIds),
          force_regenerate: forceRegenerate,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate comparison');
      }

      const data = await response.json();
      setComparisonResult({
        data: data.comparison_json,
        cached: data.cached,
        generatedAt: new Date(data.generated_at),
        modelName: data.model_name,
        loading: false,
        error: null,
      });
    } catch (error) {
      console.error('Error generating comparison:', error);
      setComparisonResult(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to generate comparison',
      }));
      showToast(error instanceof Error ? error.message : 'Failed to generate comparison');
    }
  }, [selectedIds, validateSelection, showToast]);

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
    setSummaryResult({ data: null, cached: false, generatedAt: null, modelName: '', loading: false, error: null });
    setComparisonResult({ data: null, cached: false, generatedAt: null, modelName: '', loading: false, error: null });
  }, []);

  // Format date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Unknown date';
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  // Render preview panel content
  const renderPreviewContent = () => {
    if (selectedReports.length === 0) {
      return (
        <div className="preview-empty">
          <FileText size={48} strokeWidth={1.5} />
          <h3>No Report Selected</h3>
          <p>Select a report from the list to preview it here</p>
        </div>
      );
    }

    if (selectedReports.length === 1) {
      const report = selectedReports[0];
      return (
        <div className="preview-single">
          <div className="preview-header">
            <h3>{report.filename}</h3>
            <span className="preview-date">{formatDate(report.report_date || report.uploaded_at)}</span>
          </div>
          <div className="preview-frame">
            {report.file_type === '.pdf' ? (
              <iframe
                src={`${API_BASE}${report.preview_url}`}
                title={report.filename}
                className="preview-iframe"
              />
            ) : (
              <img
                src={`${API_BASE}${report.preview_url}`}
                alt={report.filename}
                className="preview-image"
              />
            )}
          </div>
        </div>
      );
    }

    // Multiple reports - grid view
    return (
      <div className="preview-multi">
        <div className="preview-multi-header">
          <Grid size={18} />
          <span>{selectedReports.length} Reports Selected</span>
        </div>
        <div className={`preview-grid grid-${Math.min(selectedReports.length, 3)}`}>
          {selectedReports.map(report => (
            <div
              key={report.id}
              className={`preview-grid-item ${focusedPreviewId === report.id ? 'focused' : ''}`}
              onClick={() => setFocusedPreviewId(focusedPreviewId === report.id ? null : report.id)}
            >
              <div className="preview-grid-item-header">
                <span className="preview-grid-filename">{report.filename}</span>
                <span className="preview-grid-date">{formatDate(report.report_date || report.uploaded_at)}</span>
              </div>
              <div className="preview-grid-content">
                {report.file_type === '.pdf' ? (
                  <iframe
                    src={`${API_BASE}${report.preview_url}#toolbar=0&navpanes=0`}
                    title={report.filename}
                    className="preview-grid-iframe"
                  />
                ) : (
                  <img
                    src={`${API_BASE}${report.preview_url}`}
                    alt={report.filename}
                    className="preview-grid-image"
                  />
                )}
              </div>
              <button
                className="preview-grid-expand"
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(`${API_BASE}${report.preview_url}`, '_blank');
                }}
              >
                <Maximize2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Render AI results panel
  const renderAIResults = () => {
    const isLoading = summaryResult.loading || comparisonResult.loading;
    
    if (selectedIds.size === 0) {
      return (
        <div className="ai-empty">
          <Sparkles size={48} strokeWidth={1.5} />
          <h3>AI Analysis</h3>
          <p>Select reports to generate AI-powered summaries and comparisons</p>
        </div>
      );
    }

    return (
      <div className="ai-panel">
        {/* Tabs */}
        <div className="ai-tabs">
          <button
            className={`ai-tab ${activeTab === 'summary' ? 'active' : ''}`}
            onClick={() => setActiveTab('summary')}
            disabled={selectedIds.size !== 1}
          >
            Summary
          </button>
          <button
            className={`ai-tab ${activeTab === 'comparison' ? 'active' : ''}`}
            onClick={() => setActiveTab('comparison')}
            disabled={selectedIds.size < 2}
          >
            Comparison
          </button>
          <button
            className={`ai-tab ${activeTab === 'metrics' ? 'active' : ''}`}
            onClick={() => setActiveTab('metrics')}
            disabled={selectedIds.size === 0}
          >
            Metrics
          </button>
        </div>

        {/* Tab Content */}
        <div className="ai-content">
          {/* Summary Tab */}
          {activeTab === 'summary' && (
            <>
              {summaryResult.loading ? (
                <div className="ai-loading">
                  <Loader2 size={32} className="spinner" />
                  <p>Generating AI summary...</p>
                </div>
              ) : summaryResult.error ? (
                <div className="ai-error">
                  <AlertCircle size={24} />
                  <p>{summaryResult.error}</p>
                  <button onClick={() => generateSummary(true)}>Retry</button>
                </div>
              ) : summaryResult.data ? (
                <div className="ai-summary">
                  <div className="ai-summary-header">
                    <h3>{summaryResult.data.title}</h3>
                    {summaryResult.cached && <span className="cache-badge">Cached</span>}
                  </div>
                  
                  <p className="ai-summary-text">{summaryResult.data.plain_language_summary}</p>
                  
                  {/* Highlights */}
                  <div className="ai-highlights">
                    {summaryResult.data.highlights.positive.length > 0 && (
                      <div className="highlight-section positive">
                        <h4><CheckCircle2 size={16} /> Positive Findings</h4>
                        <ul>
                          {summaryResult.data.highlights.positive.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {summaryResult.data.highlights.needs_attention.length > 0 && (
                      <div className="highlight-section attention">
                        <h4><AlertTriangle size={16} /> Needs Attention</h4>
                        <ul>
                          {summaryResult.data.highlights.needs_attention.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {summaryResult.data.highlights.next_steps.length > 0 && (
                      <div className="highlight-section next-steps">
                        <h4><ArrowRight size={16} /> Suggested Next Steps</h4>
                        <ul>
                          {summaryResult.data.highlights.next_steps.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Key Findings */}
                  {summaryResult.data.key_findings.length > 0 && (
                    <div className="ai-findings">
                      <h4>Key Findings</h4>
                      {summaryResult.data.key_findings.map((finding, i) => (
                        <div key={i} className="finding-item">
                          <strong>{finding.item}</strong>
                          <span>{finding.evidence}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Footer */}
                  <div className="ai-footer">
                    <span className="ai-timestamp">
                      Generated: {summaryResult.generatedAt?.toLocaleString()}
                    </span>
                    <button 
                      className="regenerate-btn"
                      onClick={() => generateSummary(true)}
                      disabled={isLoading}
                    >
                      <RefreshCw size={14} />
                      Regenerate
                    </button>
                  </div>

                  <p className="ai-disclaimer">
                    ⚕️ This is an AI-generated summary for informational purposes only. 
                    It is not a substitute for professional medical advice.
                  </p>
                </div>
              ) : (
                <div className="ai-prompt">
                  <p>Click "Generate Summary" to analyze this report</p>
                </div>
              )}
            </>
          )}

          {/* Comparison Tab */}
          {activeTab === 'comparison' && (
            <>
              {comparisonResult.loading ? (
                <div className="ai-loading">
                  <Loader2 size={32} className="spinner" />
                  <p>Comparing reports...</p>
                </div>
              ) : comparisonResult.error ? (
                <div className="ai-error">
                  <AlertCircle size={24} />
                  <p>{comparisonResult.error}</p>
                  <button onClick={() => generateComparison(true)}>Retry</button>
                </div>
              ) : comparisonResult.data ? (
                <div className="ai-comparison">
                  <div className="ai-summary-header">
                    <h3>{comparisonResult.data.title}</h3>
                    {comparisonResult.cached && <span className="cache-badge">Cached</span>}
                  </div>
                  
                  <p className="ai-overall-change">{comparisonResult.data.overall_change}</p>
                  
                  {/* Changes */}
                  <div className="ai-changes">
                    {comparisonResult.data.improvements.length > 0 && (
                      <div className="change-section improved">
                        <h4><CheckCircle2 size={16} /> Improvements</h4>
                        <ul>
                          {comparisonResult.data.improvements.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {comparisonResult.data.worsened.length > 0 && (
                      <div className="change-section worsened">
                        <h4><AlertTriangle size={16} /> Areas of Concern</h4>
                        <ul>
                          {comparisonResult.data.worsened.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {comparisonResult.data.stable.length > 0 && (
                      <div className="change-section stable">
                        <h4><Check size={16} /> Stable</h4>
                        <ul>
                          {comparisonResult.data.stable.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Key Differences */}
                  {comparisonResult.data.key_differences.length > 0 && (
                    <div className="ai-differences">
                      <h4>Key Differences</h4>
                      {comparisonResult.data.key_differences.map((diff, i) => (
                        <div key={i} className="difference-item">
                          <span className="diff-metric">{diff.metric}</span>
                          <span className="diff-change">
                            {diff.from} → {diff.to}
                          </span>
                          <span className="diff-evidence">{diff.evidence}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Next Steps */}
                  {comparisonResult.data.next_steps.length > 0 && (
                    <div className="highlight-section next-steps">
                      <h4><ArrowRight size={16} /> Recommended Actions</h4>
                      <ul>
                        {comparisonResult.data.next_steps.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Footer */}
                  <div className="ai-footer">
                    <span className="ai-timestamp">
                      Generated: {comparisonResult.generatedAt?.toLocaleString()}
                    </span>
                    <button 
                      className="regenerate-btn"
                      onClick={() => generateComparison(true)}
                      disabled={isLoading}
                    >
                      <RefreshCw size={14} />
                      Regenerate
                    </button>
                  </div>

                  <p className="ai-disclaimer">
                    ⚕️ This is an AI-generated comparison for informational purposes only. 
                    It is not a substitute for professional medical advice.
                  </p>
                </div>
              ) : (
                <div className="ai-prompt">
                  <p>Click "Compare Selected" to analyze changes between reports</p>
                </div>
              )}
            </>
          )}

          {/* Metrics Tab */}
          {activeTab === 'metrics' && (
            <div className="ai-metrics">
              <p className="metrics-placeholder">
                Key metrics extracted from selected reports will appear here.
                <br /><br />
                This feature shows structured lab values and measurements when available.
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="report-summary-page">
      <DashboardNavbar userName="User" userStatus="" />

      {/* Toast Notifications */}
      <AnimatePresence>
        {toasts.map(toast => (
          <motion.div
            key={toast.id}
            className={`toast toast-${toast.type}`}
            initial={{ opacity: 0, y: -50, x: '-50%' }}
            animate={{ opacity: 1, y: 0, x: '-50%' }}
            exit={{ opacity: 0, y: -50, x: '-50%' }}
          >
            {toast.type === 'error' && <AlertCircle size={18} />}
            {toast.type === 'warning' && <AlertTriangle size={18} />}
            {toast.type === 'success' && <CheckCircle2 size={18} />}
            <span>{toast.message}</span>
            <button onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}>
              <X size={14} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>

      <div className="report-summary-content">
        {/* Page Header */}
        <div className="page-header">
          <div className="page-header-text">
            <h1>AI Report Summary</h1>
            <p>Select reports to generate AI-powered summaries and comparisons</p>
          </div>
          {selectedIds.size > 0 && (
            <button className="clear-selection-btn" onClick={clearSelection}>
              <X size={16} />
              Clear Selection ({selectedIds.size})
            </button>
          )}
        </div>

        {/* Main Layout */}
        <div className="summary-layout">
          {/* Left Panel - Report List */}
          <div className="left-panel">
            <div className="panel-card">
              <div className="panel-header">
                <h2>Your Reports</h2>
                <span className="report-count">{filteredReports.length} reports</span>
              </div>

              {/* Search */}
              <div className="search-box">
                <Search size={18} />
                <input
                  type="text"
                  placeholder="Search reports..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              {/* Filters */}
              <div className="filter-row">
                <div className="filter-group">
                  <Filter size={14} />
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                  >
                    <option value="">All Categories</option>
                    {categories.map(cat => (
                      <option key={cat.name} value={cat.name}>
                        {cat.name} ({cat.count})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="filter-group">
                  <select
                    value={docTypeFilter}
                    onChange={(e) => setDocTypeFilter(e.target.value)}
                  >
                    <option value="">All Types</option>
                    {docTypes.map(dt => (
                      <option key={dt.name} value={dt.name}>
                        {dt.name} ({dt.count})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Selected count */}
              {selectedIds.size > 0 && (
                <div className="selected-info">
                  <Check size={16} />
                  <span>{selectedIds.size} of 6 selected</span>
                </div>
              )}

              {/* Report List */}
              <div className="report-list">
                {loading ? (
                  <div className="list-loading">
                    <Loader2 size={24} className="spinner" />
                    <span>Loading reports...</span>
                  </div>
                ) : filteredReports.length === 0 ? (
                  <div className="list-empty">
                    <FileText size={32} strokeWidth={1.5} />
                    <p>No reports found</p>
                  </div>
                ) : (
                  filteredReports.map(report => (
                    <motion.div
                      key={report.id}
                      className={`report-item ${selectedIds.has(report.id) ? 'selected' : ''}`}
                      onClick={() => toggleSelection(report.id)}
                      whileHover={{ backgroundColor: 'rgba(107, 145, 117, 0.08)' }}
                      whileTap={{ scale: 0.99 }}
                    >
                      <div className="report-checkbox">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(report.id)}
                          onChange={() => {}}
                        />
                      </div>
                      <div className="report-info">
                        <span className="report-name">{report.filename}</span>
                        <div className="report-meta">
                          <span className="report-category">
                            {report.category || 'Uncategorized'}
                          </span>
                          <span className="report-date">
                            <Calendar size={12} />
                            {formatDate(report.report_date || report.uploaded_at)}
                          </span>
                        </div>
                      </div>
                      {selectedIds.has(report.id) && (
                        <div className="selected-badge">
                          <Check size={14} />
                        </div>
                      )}
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Center Panel - Preview */}
          <div className="center-panel">
            <div className="panel-card preview-panel">
              {renderPreviewContent()}
            </div>
          </div>

          {/* Right Panel - AI Results */}
          <div className="right-panel">
            <div className="panel-card ai-results-panel">
              {renderAIResults()}
            </div>
          </div>
        </div>

        {/* Floating Action Button */}
        <AnimatePresence>
          {selectedIds.size > 0 && (
            <motion.div
              className="floating-action"
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
            >
              {selectedIds.size === 1 ? (
                <button
                  className="action-btn primary"
                  onClick={() => generateSummary()}
                  disabled={summaryResult.loading}
                >
                  {summaryResult.loading ? (
                    <Loader2 size={18} className="spinner" />
                  ) : (
                    <Sparkles size={18} />
                  )}
                  Generate Summary
                </button>
              ) : (
                <button
                  className="action-btn primary"
                  onClick={() => generateComparison()}
                  disabled={comparisonResult.loading || !validateSelection().valid}
                >
                  {comparisonResult.loading ? (
                    <Loader2 size={18} className="spinner" />
                  ) : (
                    <Sparkles size={18} />
                  )}
                  Compare Selected ({selectedIds.size})
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default ReportSummary;
