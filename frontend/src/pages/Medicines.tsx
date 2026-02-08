/**
 * Medicines Page
 * 
 * Two-section single-page design:
 * 1. Find Cheap Alternative - Upload prescription or enter medicine to find generic substitutes
 * 2. Find Nearest Pharmacy - Locate Jan Aushadhi Kendras and pharmacies nearby
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Pill, Search, Upload, MapPin, Navigation, Phone, Clock, Star,
  ChevronDown, ChevronUp, ExternalLink, Bookmark, BookmarkCheck,
  AlertCircle, CheckCircle, Loader2, X, FileText, Camera, Sparkles
} from 'lucide-react';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import { getTokenSync } from '../services/tokenService';
import { Geolocation } from '@capacitor/geolocation';
import { API_BASE_URL as API_BASE } from '../config/api';
import '../styles/dashboardTokens.css';
import '../styles/dashboardBase.css';
import './Medicines.css';

// Types
interface NormalizedMedicine {
  brand_name?: string;
  salt?: string;
  strength?: string;
  form: string;
  release_type?: string;
  raw_line: string;
  confidence: number;
}

interface Substitute {
  id: string;
  product_name: string;
  brand_name?: string;
  salt: string;
  salts?: string[];
  strength: string;
  form: string;
  dosage_form?: string;
  release_type?: string;
  mrp?: number;
  price_mrp?: number;
  manufacturer?: string;
  is_jan_aushadhi: boolean;
  source?: string;
  match_score?: number;
  match_reason?: string[];
}

interface SubstituteResult {
  query: string;
  normalized: NormalizedMedicine;
  alternatives: Substitute[];
  count: number;
  match_level?: string;
  notes: string[];
}

interface Pharmacy {
  place_id: string;
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  rating?: number;
  total_ratings?: number;
  is_open?: boolean;
  is_jan_aushadhi: boolean;
}

interface PharmacyDetails {
  place_id: string;
  name: string;
  address?: string;
  phone?: string;
  website?: string;
  google_maps_url?: string;
  latitude?: number;
  longitude?: number;
  rating?: number;
  total_ratings?: number;
  is_open?: boolean;
  hours?: string[];
  directions_url?: string;
}

export default function Medicines() {
  const navigate = useNavigate();
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [userName, setUserName] = useState<string>('User');
  const [loading, setLoading] = useState(true);

  // Section refs for smooth scrolling
  const substituteRef = useRef<HTMLDivElement>(null);
  const pharmacyRef = useRef<HTMLDivElement>(null);

  // Substitute finder state
  const [searchMode, setSearchMode] = useState<'text' | 'upload'>('text');
  const [medicineText, setMedicineText] = useState('');
  const [searchLoading, setSearchLoading] = useState(false);
  const [substituteResults, setSubstituteResults] = useState<SubstituteResult[]>([]);
  const [expandedResult, setExpandedResult] = useState<number | null>(null);
  const [savedMedicines, setSavedMedicines] = useState<Set<string>>(new Set());

  // Pharmacy finder state
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [showManualLocation, setShowManualLocation] = useState(false);
  const [manualLat, setManualLat] = useState('');
  const [manualLng, setManualLng] = useState('');
  const [pharmacyType, setPharmacyType] = useState<'all' | 'jan_aushadhi' | 'generic'>('all');
  const [pharmacies, setPharmacies] = useState<Pharmacy[]>([]);
  const [pharmacyLoading, setPharmacyLoading] = useState(false);
  const [selectedPharmacy, setSelectedPharmacy] = useState<PharmacyDetails | null>(null);
  const [showPharmacyModal, setShowPharmacyModal] = useState(false);

  // File upload ref
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const token = getTokenSync();
    if (!token) {
      navigate('/login');
      return;
    }
    setAuthToken(token);

    // Fetch user info
    fetch(`${API_BASE}/api/me/bootstrap`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.full_name) {
          setUserName(data.full_name.split(' ')[0]);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [navigate]);

  // Scroll to section
  const scrollToSection = (section: 'substitute' | 'pharmacy') => {
    const ref = section === 'substitute' ? substituteRef : pharmacyRef;
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // Search for substitutes
  const handleSearch = async () => {
    if (!medicineText.trim() || !authToken) return;

    setSearchLoading(true);
    setSubstituteResults([]);

    try {
      const formData = new FormData();
      formData.append('text', medicineText.trim());

      const response = await fetch(`${API_BASE}/api/medicines/substitutes/from-text`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to search');

      const data = await response.json();
      setSubstituteResults([data]);
      setExpandedResult(0);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setSearchLoading(false);
    }
  };

  // Handle file upload
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !authToken) return;

    setSearchLoading(true);
    setSubstituteResults([]);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/api/medicines/extract-from-image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to extract');

      const data = await response.json();

      // Get substitutes for each extracted medicine using Grok AI
      const results: SubstituteResult[] = [];
      for (const medicine of data.medicines || []) {
        // Grok returns salts as array, join them for display
        const saltStr = Array.isArray(medicine.salts)
          ? medicine.salts.join(' + ')
          : medicine.salts || medicine.salt;

        if (saltStr) {
          try {
            // Use from-text endpoint which uses Grok AI
            const formData = new FormData();
            formData.append('text', medicine.raw_line || `${medicine.brand_name} ${medicine.strength}`);

            const subResponse = await fetch(`${API_BASE}/api/medicines/substitutes/from-text`, {
              method: 'POST',
              headers: {
                Authorization: `Bearer ${authToken}`,
              },
              body: formData,
            });

            if (subResponse.ok) {
              const subData = await subResponse.json();
              results.push(subData);
            }
          } catch (e) {
            console.error('Substitute lookup error:', e);
          }
        }
      }

      setSubstituteResults(results);
      if (results.length > 0) setExpandedResult(0);
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setSearchLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Save medicine
  const handleSaveMedicine = async (medicine: NormalizedMedicine) => {
    if (!authToken) return;

    try {
      const response = await fetch(`${API_BASE}/api/medicines/saved`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_name: medicine.brand_name,
          salt: medicine.salt || '',
          strength: medicine.strength || '',
          form: medicine.form,
          release_type: medicine.release_type,
        }),
      });

      if (response.ok) {
        setSavedMedicines(prev => new Set([...prev, medicine.raw_line]));
      }
    } catch (error) {
      console.error('Save error:', error);
    }
  };

  // Get user location
  const getLocation = useCallback(async () => {
    setLocationLoading(true);
    setLocationError(null);

    try {
      // Check/Request permission for native
      const perm = await Geolocation.checkPermissions();
      if (perm.location !== 'granted') {
        const req = await Geolocation.requestPermissions();
        if (req.location !== 'granted') {
          throw new Error('Location permission denied');
        }
      }

      const position = await Geolocation.getCurrentPosition({
        enableHighAccuracy: true,
        timeout: 15000,
      });

      setUserLocation({
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      });
      setLocationLoading(false);
      setLocationError(null);
    } catch (err: any) {
      console.error('Geolocation error:', err);
      let errorMessage = 'Unable to get your location. ';

      if (err.message?.includes('denied')) {
        errorMessage = '❌ Location access denied. Please enable location permissions in your settings.';
      } else {
        errorMessage = `❌ Error: ${err.message || 'Unknown error while getting location.'}`;
      }

      setLocationError(errorMessage);
      setLocationLoading(false);
    }
  }, []);

  // Search pharmacies
  useEffect(() => {
    if (!userLocation || !authToken) return;

    const fetchPharmacies = async () => {
      setPharmacyLoading(true);
      try {
        const params = new URLSearchParams({
          latitude: userLocation.lat.toString(),
          longitude: userLocation.lng.toString(),
          radius: '5000',
          pharmacy_type: pharmacyType,
        });

        const response = await fetch(`${API_BASE}/api/medicines/pharmacies/nearby?${params}`, {
          headers: { Authorization: `Bearer ${authToken}` },
        });

        if (response.ok) {
          const data = await response.json();
          setPharmacies(data.pharmacies || []);
        }
      } catch (error) {
        console.error('Pharmacy search error:', error);
      } finally {
        setPharmacyLoading(false);
      }
    };

    fetchPharmacies();
  }, [userLocation, pharmacyType, authToken]);

  // Get pharmacy details
  const handlePharmacyClick = async (pharmacy: Pharmacy) => {
    if (!authToken) return;

    try {
      const response = await fetch(`${API_BASE}/api/medicines/pharmacies/${pharmacy.place_id}`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });

      if (response.ok) {
        const details = await response.json();
        setSelectedPharmacy(details);
        setShowPharmacyModal(true);

        // Log click
        fetch(`${API_BASE}/api/medicines/pharmacies/${pharmacy.place_id}/click?action=view`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${authToken}` },
        }).catch(() => { });
      }
    } catch (error) {
      console.error('Pharmacy details error:', error);
    }
  };

  if (loading) {
    return (
      <div className="medicines-page dashboard-page">
        <DashboardNavbar userName="Loading..." userStatus="" />
        <div className="medicines-loading">
          <Loader2 className="spin" size={32} />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="medicines-page dashboard-page">
      {/* Background */}
      <div className="dashboard-background">
        <div className="dashboard-bg-blob dashboard-bg-blob-1" />
        <div className="dashboard-bg-blob dashboard-bg-blob-2" />
      </div>

      <DashboardNavbar userName={userName} userStatus="" />

      <div className="dashboard-content">
        <div className="dashboard-container">
          {/* Page Header */}
          <motion.div
            className="dashboard-header"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="dashboard-welcome">
              <div className="dashboard-welcome-text">
                <h1>
                  <Pill className="header-icon" size={28} />
                  Medicine Tools
                </h1>
                <p>Find affordable alternatives and nearby pharmacies</p>
              </div>
            </div>

            {/* Quick Nav Buttons */}
            <div className="section-nav-buttons">
              <motion.button
                className="section-nav-btn"
                onClick={() => scrollToSection('substitute')}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Sparkles size={18} />
                Find Cheap Alternative
              </motion.button>
              <motion.button
                className="section-nav-btn"
                onClick={() => scrollToSection('pharmacy')}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <MapPin size={18} />
                Find Nearest Pharmacy
              </motion.button>
            </div>
          </motion.div>

          {/* Section 1: Find Cheap Alternative */}
          <motion.section
            ref={substituteRef}
            className="medicines-section"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <div className="section-header">
              <div className="section-title">
                <Sparkles className="section-icon" size={24} />
                <div>
                  <h2>Find Cheap Alternative</h2>
                  <p>Search generic substitutes for your prescribed medicines</p>
                </div>
              </div>
            </div>

            {/* Search Input Area */}
            <div className="search-area">
              {/* Mode Toggle */}
              <div className="search-mode-toggle">
                <button
                  className={`mode-btn ${searchMode === 'text' ? 'active' : ''}`}
                  onClick={() => setSearchMode('text')}
                >
                  <Search size={16} />
                  Type Medicine
                </button>
                <button
                  className={`mode-btn ${searchMode === 'upload' ? 'active' : ''}`}
                  onClick={() => setSearchMode('upload')}
                >
                  <Camera size={16} />
                  Upload Prescription
                </button>
              </div>

              {searchMode === 'text' ? (
                <div className="text-search">
                  <div className="search-input-wrapper">
                    <Search className="search-icon" size={20} />
                    <input
                      type="text"
                      placeholder="Enter medicine name (e.g., Crocin 500mg, Metformin 500mg SR)"
                      value={medicineText}
                      onChange={(e) => setMedicineText(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                      className="medicine-search-input"
                    />
                  </div>
                  <motion.button
                    className="search-btn"
                    onClick={handleSearch}
                    disabled={!medicineText.trim() || searchLoading}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {searchLoading ? (
                      <Loader2 className="spin" size={20} />
                    ) : (
                      <>
                        <Search size={20} />
                        Find Alternatives
                      </>
                    )}
                  </motion.button>
                </div>
              ) : (
                <div className="upload-area">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.pdf"
                    onChange={handleFileUpload}
                    className="file-input"
                    id="prescription-upload"
                  />
                  <label htmlFor="prescription-upload" className="upload-label">
                    {searchLoading ? (
                      <>
                        <Loader2 className="spin" size={48} />
                        <span>Extracting medicines...</span>
                      </>
                    ) : (
                      <>
                        <Upload size={48} />
                        <span>Click or drag to upload prescription</span>
                        <small>Supports: JPG, PNG, PDF</small>
                      </>
                    )}
                  </label>
                </div>
              )}
            </div>

            {/* Results */}
            <AnimatePresence mode="wait">
              {substituteResults.length > 0 && (
                <motion.div
                  className="substitute-results"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <h3>
                    <FileText size={18} />
                    Found {substituteResults.length} medicine{substituteResults.length > 1 ? 's' : ''}
                  </h3>

                  {substituteResults.map((result, index) => (
                    <motion.div
                      key={index}
                      className="result-card"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      {/* Original Medicine */}
                      <div
                        className="result-header"
                        onClick={() => setExpandedResult(expandedResult === index ? null : index)}
                      >
                        <div className="result-medicine-info">
                          <span className="medicine-name">
                            {result.normalized.brand_name || result.normalized.salt || result.normalized.raw_line}
                          </span>
                          <span className="medicine-details">
                            {result.normalized.salt && <span className="salt">{result.normalized.salt}</span>}
                            {result.normalized.strength && <span className="strength">{result.normalized.strength}</span>}
                            {result.normalized.form && <span className="form">{result.normalized.form}</span>}
                            {result.normalized.release_type && (
                              <span className="release">{result.normalized.release_type}</span>
                            )}
                          </span>
                        </div>
                        <div className="result-actions">
                          <span className="substitute-count">
                            {result.count} substitute{result.count !== 1 ? 's' : ''}
                          </span>
                          <button
                            className="save-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSaveMedicine(result.normalized);
                            }}
                            title="Save to my medicines"
                          >
                            {savedMedicines.has(result.normalized.raw_line) ? (
                              <BookmarkCheck size={18} />
                            ) : (
                              <Bookmark size={18} />
                            )}
                          </button>
                          {expandedResult === index ? (
                            <ChevronUp size={20} />
                          ) : (
                            <ChevronDown size={20} />
                          )}
                        </div>
                      </div>

                      {/* Substitutes List */}
                      <AnimatePresence>
                        {expandedResult === index && (
                          <motion.div
                            className="substitutes-list"
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                          >
                            {result.alternatives && result.alternatives.length > 0 ? (
                              <>
                                <div className="substitutes-header">
                                  <span>Product</span>
                                  <span>Manufacturer</span>
                                  <span>MRP</span>
                                </div>
                                {result.alternatives.map((sub) => (
                                  <div
                                    key={sub.id}
                                    className={`substitute-item ${sub.is_jan_aushadhi ? 'jan-aushadhi' : ''}`}
                                  >
                                    <div className="sub-name">
                                      {sub.brand_name || sub.product_name}
                                      {sub.is_jan_aushadhi && (
                                        <span className="jan-badge">Jan Aushadhi</span>
                                      )}
                                      {sub.match_score && (
                                        <span
                                          className={`match-score-badge ${sub.match_score === 1.0 ? 'exact' :
                                            sub.match_score >= 0.8 ? 'near' :
                                              sub.match_score >= 0.6 ? 'partial' : 'generic'
                                            }`}
                                          title={sub.match_reason?.join(', ')}
                                        >
                                          {Math.round(sub.match_score * 100)}%
                                        </span>
                                      )}
                                    </div>
                                    <div className="sub-manufacturer">
                                      {sub.manufacturer || '-'}
                                    </div>
                                    <div className="sub-price">
                                      {sub.price_mrp ? `₹${sub.price_mrp.toFixed(2)}` : (sub.mrp ? `₹${sub.mrp.toFixed(2)}` : '-')}
                                    </div>
                                  </div>
                                ))}
                                {result.notes && result.notes.length > 0 && (
                                  <div className="disclaimer">
                                    <AlertCircle size={14} />
                                    <div>
                                      {result.notes.map((note, i) => (
                                        <div key={i}>{note}</div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </>
                            ) : (
                              <div className="no-substitutes">
                                <AlertCircle size={20} />
                                <div>
                                  <span>No alternatives found in our database yet</span>
                                  {result.notes && result.notes.length > 0 && (
                                    <div style={{ marginTop: '8px', fontSize: '13px', opacity: 0.8 }}>
                                      {result.notes.map((note, i) => (
                                        <div key={i}>{note}</div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.section>

          {/* Section 2: Find Nearest Pharmacy */}
          <motion.section
            ref={pharmacyRef}
            className="medicines-section pharmacy-section"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="section-header">
              <div className="section-title">
                <MapPin className="section-icon" size={24} />
                <div>
                  <h2>Find Nearest Pharmacy</h2>
                  <p>Locate Jan Aushadhi Kendras and medical stores near you</p>
                </div>
              </div>
            </div>

            {/* Location Area */}
            <div className="location-area">
              {!userLocation ? (
                <div className="location-request">
                  <MapPin size={48} className="location-icon" />
                  <h3>Enable Location</h3>
                  <p>Share your location to find pharmacies nearby</p>
                  <motion.button
                    className="location-btn"
                    onClick={getLocation}
                    disabled={locationLoading}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {locationLoading ? (
                      <>
                        <Loader2 className="spin" size={20} />
                        Getting location...
                      </>
                    ) : (
                      <>
                        <Navigation size={20} />
                        Share My Location
                      </>
                    )}
                  </motion.button>
                  {locationError && (
                    <div className="location-error">
                      <AlertCircle size={16} />
                      <div>
                        <div>{locationError}</div>
                        <button
                          className="text-link"
                          onClick={() => setShowManualLocation(true)}
                          style={{ marginTop: '8px', textDecoration: 'underline', cursor: 'pointer', background: 'none', border: 'none', color: 'var(--dash-accent)' }}
                        >
                          Enter location manually instead
                        </button>
                      </div>
                    </div>
                  )}

                  {showManualLocation && (
                    <motion.div
                      className="manual-location-input"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      style={{ marginTop: '16px', padding: '16px', background: 'var(--dash-card-bg)', borderRadius: '8px' }}
                    >
                      <p style={{ marginBottom: '12px', fontSize: '14px' }}>Enter your coordinates:</p>
                      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                        <input
                          type="number"
                          placeholder="Latitude (e.g., 28.6139)"
                          value={manualLat}
                          onChange={(e) => setManualLat(e.target.value)}
                          style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid var(--dash-border)' }}
                          step="any"
                        />
                        <input
                          type="number"
                          placeholder="Longitude (e.g., 77.2090)"
                          value={manualLng}
                          onChange={(e) => setManualLng(e.target.value)}
                          style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid var(--dash-border)' }}
                          step="any"
                        />
                      </div>
                      <button
                        className="location-btn"
                        onClick={() => {
                          const lat = parseFloat(manualLat);
                          const lng = parseFloat(manualLng);
                          if (!isNaN(lat) && !isNaN(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
                            setUserLocation({ lat, lng });
                            setLocationError(null);
                            setShowManualLocation(false);
                          } else {
                            setLocationError('Invalid coordinates. Lat: -90 to 90, Lng: -180 to 180');
                          }
                        }}
                        style={{ width: '100%' }}
                      >
                        Use This Location
                      </button>
                      <p style={{ marginTop: '8px', fontSize: '12px', opacity: 0.7 }}>
                        💡 Tip: Search "my coordinates" on Google to find yours
                      </p>
                    </motion.div>
                  )}
                </div>
              ) : (
                <>
                  {/* Filter Buttons */}
                  <div className="pharmacy-filters">
                    <button
                      className={`filter-btn ${pharmacyType === 'all' ? 'active' : ''}`}
                      onClick={() => setPharmacyType('all')}
                    >
                      All Pharmacies
                    </button>
                    <button
                      className={`filter-btn jan ${pharmacyType === 'jan_aushadhi' ? 'active' : ''}`}
                      onClick={() => setPharmacyType('jan_aushadhi')}
                    >
                      🏥 Jan Aushadhi Only
                    </button>
                    <button
                      className={`filter-btn ${pharmacyType === 'generic' ? 'active' : ''}`}
                      onClick={() => setPharmacyType('generic')}
                    >
                      Generic Stores
                    </button>
                  </div>

                  {/* Pharmacy List */}
                  {pharmacyLoading ? (
                    <div className="pharmacy-loading">
                      <Loader2 className="spin" size={32} />
                      <p>Finding pharmacies...</p>
                    </div>
                  ) : pharmacies.length > 0 ? (
                    <div className="pharmacy-list">
                      {pharmacies.map((pharmacy) => (
                        <motion.div
                          key={pharmacy.place_id}
                          className={`pharmacy-card ${pharmacy.is_jan_aushadhi ? 'jan-aushadhi' : ''}`}
                          onClick={() => handlePharmacyClick(pharmacy)}
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.99 }}
                        >
                          <div className="pharmacy-info">
                            <div className="pharmacy-name">
                              {pharmacy.name}
                              {pharmacy.is_jan_aushadhi && (
                                <span className="jan-badge">Jan Aushadhi</span>
                              )}
                            </div>
                            <div className="pharmacy-address">
                              <MapPin size={14} />
                              {pharmacy.address}
                            </div>
                            <div className="pharmacy-meta">
                              {pharmacy.rating && (
                                <span className="rating">
                                  <Star size={14} fill="currentColor" />
                                  {pharmacy.rating}
                                  {pharmacy.total_ratings && ` (${pharmacy.total_ratings})`}
                                </span>
                              )}
                              <span className={`status ${pharmacy.is_open ? 'open' : 'closed'}`}>
                                {pharmacy.is_open ? (
                                  <>
                                    <CheckCircle size={14} />
                                    Open
                                  </>
                                ) : (
                                  <>
                                    <Clock size={14} />
                                    Closed
                                  </>
                                )}
                              </span>
                            </div>
                          </div>
                          <ExternalLink size={20} className="view-icon" />
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <div className="no-pharmacies">
                      <MapPin size={48} />
                      <p>No pharmacies found nearby</p>
                      <small>Try expanding the search radius or changing filters</small>
                    </div>
                  )}
                </>
              )}
            </div>
          </motion.section>
        </div>
      </div>

      {/* Pharmacy Details Modal */}
      <AnimatePresence>
        {showPharmacyModal && selectedPharmacy && (
          <motion.div
            className="modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowPharmacyModal(false)}
          >
            <motion.div
              className="pharmacy-modal"
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className="modal-close"
                onClick={() => setShowPharmacyModal(false)}
              >
                <X size={24} />
              </button>

              <div className="modal-content">
                <h2>{selectedPharmacy.name}</h2>

                <div className="modal-info">
                  {selectedPharmacy.address && (
                    <div className="info-row">
                      <MapPin size={18} />
                      <span>{selectedPharmacy.address}</span>
                    </div>
                  )}
                  {selectedPharmacy.phone && (
                    <div className="info-row">
                      <Phone size={18} />
                      <a href={`tel:${selectedPharmacy.phone}`}>{selectedPharmacy.phone}</a>
                    </div>
                  )}
                  {selectedPharmacy.rating && (
                    <div className="info-row">
                      <Star size={18} fill="currentColor" />
                      <span>
                        {selectedPharmacy.rating} rating
                        {selectedPharmacy.total_ratings && ` (${selectedPharmacy.total_ratings} reviews)`}
                      </span>
                    </div>
                  )}
                </div>

                {selectedPharmacy.hours && selectedPharmacy.hours.length > 0 && (
                  <div className="modal-hours">
                    <h3>
                      <Clock size={18} />
                      Opening Hours
                    </h3>
                    <ul>
                      {selectedPharmacy.hours.map((hour, i) => (
                        <li key={i}>{hour}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="modal-actions">
                  {selectedPharmacy.directions_url && (
                    <a
                      href={selectedPharmacy.directions_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="action-btn primary"
                    >
                      <Navigation size={18} />
                      Get Directions
                    </a>
                  )}
                  {selectedPharmacy.phone && (
                    <a
                      href={`tel:${selectedPharmacy.phone}`}
                      className="action-btn"
                    >
                      <Phone size={18} />
                      Call
                    </a>
                  )}
                  {selectedPharmacy.website && (
                    <a
                      href={selectedPharmacy.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="action-btn"
                    >
                      <ExternalLink size={18} />
                      Website
                    </a>
                  )}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
