/**
 * YouTubeRecommendationsCard – Smart video recommendations for organ health
 * 
 * Uses OpenRouter AI to generate video recommendations (no YouTube API needed)
 * FIXED: Stable fetch with caching, no infinite loops
 */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Youtube, ExternalLink, Loader2, AlertCircle, PlayCircle, Clock } from 'lucide-react';
import type { OrganResult } from '../../services/physicsApi';
import { generateVideoRecommendations, type AbnormalMetric, type VideoRecommendation } from '../../services/openRouterService';

interface YouTubeRecommendationsCardProps {
  selectedOrgan: string | null;
  organResult: OrganResult | null;
  currentMetrics: Record<string, number>;
}

const ORGAN_LABELS: Record<string, string> = {
  kidney: 'Kidney',
  heart: 'Heart',
  liver: 'Liver',
  lungs: 'Lungs',
  brain: 'Brain',
  blood: 'Blood',
};

// Reference ranges for metrics
const METRIC_RANGES: Record<string, { min: number; max: number }> = {
  creatinine: { min: 0.6, max: 1.2 },
  urea: { min: 7, max: 20 },
  alt: { min: 7, max: 56 },
  ast: { min: 10, max: 40 },
  bilirubin_total: { min: 0.1, max: 1.2 },
  systolic_bp: { min: 90, max: 120 },
  diastolic_bp: { min: 60, max: 80 },
  heart_rate: { min: 60, max: 100 },
  glucose: { min: 70, max: 100 },
  spo2: { min: 95, max: 100 },
  sodium: { min: 136, max: 145 },
  potassium: { min: 3.5, max: 5.0 },
};

const YouTubeRecommendationsCard: React.FC<YouTubeRecommendationsCardProps> = ({
  selectedOrgan,
  organResult,
  currentMetrics,
}) => {
  const [videos, setVideos] = useState<VideoRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Cache videos per organ to avoid refetching
  const cacheRef = useRef<Map<string, VideoRecommendation[]>>(new Map());
  
  // Track current request to ignore stale responses
  const requestIdRef = useRef(0);
  
  // AbortController for cancelling requests
  const abortControllerRef = useRef<AbortController | null>(null);

  // Calculate abnormal metrics
  const getAbnormalMetrics = (metrics: Record<string, number>): AbnormalMetric[] => {
    const abnormal: AbnormalMetric[] = [];

    for (const [metricKey, value] of Object.entries(metrics)) {
      const range = METRIC_RANGES[metricKey];
      if (!range || typeof value !== 'number') continue;

      if (value < range.min) {
        abnormal.push({
          name: metricKey,
          value,
          normalRange: `${range.min}-${range.max}`,
          status: 'low',
        });
      } else if (value > range.max) {
        abnormal.push({
          name: metricKey,
          value,
          normalRange: `${range.min}-${range.max}`,
          status: 'high',
        });
      }
    }

    return abnormal;
  };

  useEffect(() => {
    // Clear state if no organ selected
    if (!selectedOrgan || !organResult) {
      setVideos([]);
      setLoading(false);
      setError(null);
      return;
    }

    // Check cache first
    const cached = cacheRef.current.get(selectedOrgan);
    if (cached) {
      setVideos(cached);
      setLoading(false);
      setError(null);
      return;
    }

    // Abort previous request if still running
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Start new fetch
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    
    const currentRequestId = ++requestIdRef.current;
    
    const fetchRecommendations = async () => {
      setLoading(true);
      setError(null);

      try {
        const abnormalMetrics = getAbnormalMetrics(currentMetrics);
        
        // Generate video recommendations using OpenRouter AI
        const recommendations = await generateVideoRecommendations(
          ORGAN_LABELS[selectedOrgan] || selectedOrgan,
          abnormalMetrics
        );
        
        // Only update if this is still the latest request
        if (currentRequestId === requestIdRef.current && !abortController.signal.aborted) {
          setVideos(recommendations);
          // Cache the results
          cacheRef.current.set(selectedOrgan, recommendations);
          setError(null);
        }
      } catch (err: any) {
        // Only show error if request wasn't aborted
        if (!abortController.signal.aborted && currentRequestId === requestIdRef.current) {
          console.error('Error fetching recommendations:', err);
          setError(err.message || 'Failed to load recommendations');
          setVideos([]);
        }
      } finally {
        // Only clear loading if this is still the latest request
        if (currentRequestId === requestIdRef.current && !abortController.signal.aborted) {
          setLoading(false);
        }
      }
    };

    fetchRecommendations();

    // Cleanup: abort request on unmount or organ change
    return () => {
      abortController.abort();
    };
  }, [selectedOrgan]); // ONLY depend on selectedOrgan, not currentMetrics!

  const handleRetry = () => {
    // Clear cache for this organ and refetch
    if (selectedOrgan) {
      cacheRef.current.delete(selectedOrgan);
      // Trigger refetch by incrementing request ID
      requestIdRef.current++;
      
      const fetchRecommendations = async () => {
        if (!selectedOrgan || !organResult) return;
        
        setLoading(true);
        setError(null);

        try {
          const abnormalMetrics = getAbnormalMetrics(currentMetrics);
          const recommendations = await generateVideoRecommendations(
            ORGAN_LABELS[selectedOrgan] || selectedOrgan,
            abnormalMetrics
          );
          
          setVideos(recommendations);
          cacheRef.current.set(selectedOrgan, recommendations);
          setError(null);
        } catch (err: any) {
          console.error('Error fetching recommendations:', err);
          setError(err.message || 'Failed to load recommendations');
        } finally {
          setLoading(false);
        }
      };

      fetchRecommendations();
    }
  };

  const openVideo = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  if (!selectedOrgan || !organResult) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden flex flex-col h-full">
        <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-emerald-50 to-teal-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Youtube className="text-emerald-600" size={24} />
              <h3 className="text-lg font-semibold text-gray-900">Improve Your Health</h3>
            </div>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center text-gray-500 space-y-2">
            <Youtube size={48} className="mx-auto opacity-30" />
            <p className="text-sm font-medium">All organs performing well!</p>
            <p className="text-xs text-gray-400">No specific recommendations needed</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dash-card h-full flex flex-col">
      {/* Header */}
      <div className="dash-card-header">
        <h3 className="dash-card-title flex items-center gap-2">
          <Youtube size={18} />
          Improve Your Health
        </h3>
        <span className={`dash-badge dash-badge-${organResult.status === 'Healthy' ? 'success' : organResult.status === 'Watch' ? 'warning' : 'danger'}`}>
          {ORGAN_LABELS[selectedOrgan]}
        </span>
      </div>

      {/* Content */}
      <div className="dash-card-body flex-1" style={{ maxHeight: '500px', overflowY: 'auto' }}>
        <AnimatePresence mode="wait">
          {loading && (
            <motion.div
              key="loading"
              style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem 0' }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Loader2 size={32} className="animate-spin" style={{ color: 'var(--dash-accent)' }} />
              <p style={{ fontSize: '0.875rem', color: 'var(--dash-text-secondary)', marginTop: '0.75rem' }}>Finding best videos for you...</p>
            </motion.div>
          )}

          {error && !loading && (
            <motion.div
              key="error"
              style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem 0', textAlign: 'center' }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <AlertCircle size={32} style={{ color: 'var(--dash-danger)' }} />
              <p style={{ fontSize: '0.875rem', color: 'var(--dash-text-secondary)', margin: '0.75rem 0' }}>{error}</p>
              <button
                onClick={handleRetry}
                className="dash-btn dash-btn-primary"
              >
                Try Again
              </button>
            </motion.div>
          )}

          {!loading && !error && videos.length > 0 && (
            <motion.div
              key="videos"
              className="space-y-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {videos.map((video, index) => (
                <motion.div
                  key={`${video.title}-${index}`}
                  style={{
                    background: 'var(--dash-surface)',
                    border: '1px solid var(--dash-border-light)',
                    borderRadius: 'var(--dash-radius-lg)',
                    padding: '1rem',
                    marginBottom: '0.75rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    gap: '1rem',
                  }}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => openVideo(video.url)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.border = '1px solid var(--dash-accent-light)';
                    e.currentTarget.style.boxShadow = 'var(--dash-shadow-md)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.border = '1px solid var(--dash-border-light)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  {/* Thumbnail */}
                  <div style={{
                    flexShrink: 0,
                    width: '120px',
                    height: '80px',
                    background: 'linear-gradient(135deg, var(--dash-accent-pale), var(--dash-accent-light))',
                    borderRadius: 'var(--dash-radius-md)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    overflow: 'hidden',
                  }}>
                    <Youtube size={32} style={{ color: 'var(--dash-accent)', opacity: 0.5 }} />
                    <div style={{
                      position: 'absolute',
                      inset: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'opacity 0.2s',
                    }}>
                      <PlayCircle size={32} style={{ color: 'white', opacity: 0.8 }} />
                    </div>
                  </div>

                  {/* Video Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <h4 style={{
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      color: 'var(--dash-text)',
                      marginBottom: '0.25rem',
                      lineHeight: 1.3,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>
                      {video.title}
                    </h4>
                    <p style={{
                      fontSize: '0.75rem',
                      color: 'var(--dash-text-secondary)',
                      marginBottom: '0.5rem',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>
                      {video.description}
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--dash-text-muted)' }}>
                      <Clock size={12} />
                      <span>{video.duration}</span>
                    </div>
                  </div>

                  {/* External Link Icon */}
                  <div style={{ flexShrink: 0 }}>
                    <ExternalLink size={16} style={{ color: 'var(--dash-text-muted)' }} />
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}

          {!loading && !error && videos.length === 0 && (
            <motion.div
              key="empty"
              style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem 0', textAlign: 'center' }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Youtube size={48} style={{ color: 'var(--dash-border)', opacity: 0.5 }} />
              <p style={{ fontSize: '0.875rem', color: 'var(--dash-text-muted)', marginTop: '0.5rem' }}>No recommendations available</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default YouTubeRecommendationsCard;
