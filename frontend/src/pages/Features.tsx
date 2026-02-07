import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Brain,
    Network,
    Sparkles,
    ArrowRight,
    ChevronDown,
    Database,
    Cpu,
    Zap,
    Link2,
    Check,
    RefreshCw,
    AlertCircle,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import MemoryDashboard from '../components/MemoryDashboard';
import HealthGraph from '../components/HealthGraph';
import { API_BASE_URL } from '../config/api';
import '../styles/dashboardTokens.css';
import '../styles/dashboardBase.css';
import './Features.css';

function Features() {
    const navigate = useNavigate();
    const location = useLocation();
    const [authToken, setAuthToken] = useState<string | null>(null);
    const [userName, setUserName] = useState('User');
    const [loading, setLoading] = useState(true);

    // Sync overlay state – activated when arriving from profile completion
    const fromProfileSync = !!(location.state as { fromProfileSync?: boolean })?.fromProfileSync;
    const [syncOverlayVisible, setSyncOverlayVisible] = useState(fromProfileSync);
    const [syncPhase, setSyncPhase] = useState<'preparing' | 'memory' | 'graph' | 'done' | 'error'>('preparing');
    const [syncResult, setSyncResult] = useState<{
        factsSynced: number;
        memoryOk: boolean;
        graphOk: boolean;
        errors: string[];
    } | null>(null);
    // Key used to force-remount child components after sync completes
    const [syncKey, setSyncKey] = useState(0);

    // Clears router state so a page refresh doesn't re-trigger the overlay
    useEffect(() => {
        if (fromProfileSync) {
            window.history.replaceState({}, document.title);
        }
    }, [fromProfileSync]);

    // ---- Profile→Memory/Graph sync logic ----
    const runProfileSync = useCallback(async (token: string) => {
        setSyncPhase('preparing');
        // Small visual delay so the user sees the "preparing" step
        await new Promise(r => setTimeout(r, 800));

        setSyncPhase('memory');

        try {
            const response = await fetch(`${API_BASE_URL}/api/profile/sync-to-memory`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });

            const payload = await response.json().catch(() => null);

            if (!response.ok || payload?.success === false) {
                throw new Error(payload?.message || `Sync failed (${response.status})`);
            }

            const synced = payload?.synced ?? {};
            // Transition through the "graph" visual phase
            setSyncPhase('graph');
            await new Promise(r => setTimeout(r, 600));

            setSyncResult({
                factsSynced: synced.facts_synced ?? 0,
                memoryOk: !!synced.memory,
                graphOk: !!synced.graph,
                errors: payload?.errors ?? [],
            });
            setSyncPhase('done');

            // Force child re-mount so they fetch fresh data
            setSyncKey(prev => prev + 1);

            // Auto-dismiss overlay after a brief pause
            setTimeout(() => setSyncOverlayVisible(false), 2200);
        } catch (err) {
            console.error('Profile sync error:', err);
            setSyncResult({
                factsSynced: 0,
                memoryOk: false,
                graphOk: false,
                errors: [err instanceof Error ? err.message : 'Unknown error'],
            });
            setSyncPhase('error');
            // Auto-dismiss error overlay after longer pause
            setTimeout(() => setSyncOverlayVisible(false), 3500);
        }
    }, []);

    useEffect(() => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            navigate('/login');
            return;
        }
        setAuthToken(token);

        // Fetch user info
        fetch(`${API_BASE_URL}/api/me/bootstrap`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then(res => res.json())
            .then(data => {
                setUserName(data.full_name?.split(' ')[0] || 'User');
            })
            .catch(console.error)
            .finally(() => setLoading(false));

        // If arriving from profile completion, trigger the sync
        if (fromProfileSync) {
            runProfileSync(token);
        }
    }, [navigate, fromProfileSync, runProfileSync]);

    if (loading) {
        return (
            <div className="features-page">
                <DashboardNavbar userName="Loading..." userStatus="" />
                <div className="features-loading">
                    <div className="loading-spinner" />
                    <p>Loading features...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="features-page">
            {/* Background */}
            <div className="features-background">
                <div className="features-bg-blob features-bg-blob-1" />
                <div className="features-bg-blob features-bg-blob-2" />
                <div className="features-bg-blob features-bg-blob-3" />
            </div>

            <DashboardNavbar userName={userName} userStatus="" />

            {/* Profile Sync Overlay */}
            <AnimatePresence>
                {syncOverlayVisible && (
                    <motion.div
                        className="sync-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.35 }}
                    >
                        <motion.div
                            className="sync-overlay-card"
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            transition={{ type: 'spring', stiffness: 200, damping: 22 }}
                        >
                            {/* Animated header icon */}
                            <motion.div
                                className="sync-overlay-icon"
                                animate={syncPhase === 'done' ? { scale: [1, 1.15, 1] } : { rotate: 360 }}
                                transition={
                                    syncPhase === 'done'
                                        ? { duration: 0.4 }
                                        : { repeat: Infinity, duration: 1.8, ease: 'linear' }
                                }
                            >
                                {syncPhase === 'done' ? (
                                    <Check size={32} />
                                ) : syncPhase === 'error' ? (
                                    <AlertCircle size={32} />
                                ) : (
                                    <RefreshCw size={32} />
                                )}
                            </motion.div>

                            <h2 className="sync-overlay-title">
                                {syncPhase === 'done'
                                    ? 'All Set!'
                                    : syncPhase === 'error'
                                        ? 'Sync Issue'
                                        : 'Syncing Your Health Data'}
                            </h2>

                            {/* Step indicators */}
                            <div className="sync-steps">
                                <SyncStep
                                    label="Analysing profile"
                                    active={syncPhase === 'preparing'}
                                    done={syncPhase !== 'preparing'}
                                    icon={<Database size={16} />}
                                />
                                <SyncStep
                                    label="Syncing to Health Memory"
                                    active={syncPhase === 'memory'}
                                    done={['graph', 'done'].includes(syncPhase)}
                                    icon={<Brain size={16} />}
                                />
                                <SyncStep
                                    label="Building Knowledge Graph"
                                    active={syncPhase === 'graph'}
                                    done={syncPhase === 'done'}
                                    icon={<Network size={16} />}
                                />
                            </div>

                            {/* Result summary */}
                            {syncPhase === 'done' && syncResult && (
                                <motion.p
                                    className="sync-overlay-summary"
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                >
                                    {syncResult.factsSynced} facts synced
                                    {syncResult.memoryOk && ' to Memory'}
                                    {syncResult.memoryOk && syncResult.graphOk && ' &'}
                                    {syncResult.graphOk && ' Knowledge Graph'}
                                </motion.p>
                            )}

                            {syncPhase === 'error' && syncResult && (
                                <motion.p
                                    className="sync-overlay-error"
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                >
                                    {syncResult.errors[0] || 'Something went wrong. Your data is safe — sync will retry later.'}
                                </motion.p>
                            )}
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="features-content">
                <div className="features-container">

                    {/* Hero Section */}
                    <motion.section
                        className="features-hero"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                    >
                        <div className="hero-badge">
                            <Sparkles size={14} />
                            <span>Intelligent Health Engine</span>
                        </div>

                        <h1>
                            <span className="gradient-text">Breathable</span> Recommendations
                        </h1>

                        <p className="hero-description">
                            Your health insights are powered by advanced memory and knowledge graph systems.
                            Every recommendation is personalized, contextual, and traceable to its source.
                        </p>

                        <div className="hero-features">
                            <div className="hero-feature">
                                <div className="hero-feature-icon memory">
                                    <Brain size={20} />
                                </div>
                                <div className="hero-feature-content">
                                    <h4>Mem0 Memory Layer</h4>
                                    <p>Stores your preferences, facts, and health context for personalized care</p>
                                </div>
                            </div>

                            <div className="hero-feature">
                                <div className="hero-feature-icon graph">
                                    <Network size={20} />
                                </div>
                                <div className="hero-feature-content">
                                    <h4>Neo4j Knowledge Graph</h4>
                                    <p>Maps relationships between conditions, medications, and health factors</p>
                                </div>
                            </div>

                            <div className="hero-feature">
                                <div className="hero-feature-icon ai">
                                    <Cpu size={20} />
                                </div>
                                <div className="hero-feature-content">
                                    <h4>Groq LLM Integration</h4>
                                    <p>Generates evidence-based recommendations from your complete health profile</p>
                                </div>
                            </div>
                        </div>

                        <motion.div
                            className="scroll-indicator"
                            animate={{ y: [0, 8, 0] }}
                            transition={{ repeat: Infinity, duration: 1.5 }}
                        >
                            <ChevronDown size={24} />
                        </motion.div>
                    </motion.section>

                    {/* How It Works */}
                    <motion.section
                        className="features-flow"
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        viewport={{ once: true }}
                    >
                        <h2>How Your Data Flows</h2>
                        <div className="flow-diagram">
                            <div className="flow-step">
                                <div className="flow-icon">
                                    <Database size={24} />
                                </div>
                                <span>Profile & Reports</span>
                            </div>
                            <ArrowRight className="flow-arrow" />
                            <div className="flow-step">
                                <div className="flow-icon memory">
                                    <Brain size={24} />
                                </div>
                                <span>Memory Layer</span>
                            </div>
                            <ArrowRight className="flow-arrow" />
                            <div className="flow-step">
                                <div className="flow-icon graph">
                                    <Network size={24} />
                                </div>
                                <span>Knowledge Graph</span>
                            </div>
                            <ArrowRight className="flow-arrow" />
                            <div className="flow-step">
                                <div className="flow-icon ai">
                                    <Zap size={24} />
                                </div>
                                <span>AI Recommendations</span>
                            </div>
                        </div>
                    </motion.section>

                    {/* Memory Dashboard Section */}
                    <motion.section
                        className="features-section"
                        initial={{ opacity: 0, y: 30 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.5 }}
                    >
                        <div className="section-header">
                            <div className="section-header-left">
                                <Brain size={24} className="section-icon memory" />
                                <div>
                                    <h2>Health Memory</h2>
                                    <p>Your preferences and facts stored for personalized recommendations</p>
                                </div>
                            </div>
                            <div className="section-badge">
                                <Database size={14} />
                                <span>Powered by Mem0</span>
                            </div>
                        </div>

                        <div className="section-content">
                            <MemoryDashboard
                                key={`mem-${syncKey}`}
                                authToken={authToken || undefined}
                                apiBaseUrl={API_BASE_URL}
                                defaultCollapsed={false}
                            />
                        </div>
                    </motion.section>

                    {/* Health Graph Section */}
                    <motion.section
                        className="features-section"
                        initial={{ opacity: 0, y: 30 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.5 }}
                    >
                        <div className="section-header">
                            <div className="section-header-left">
                                <Network size={24} className="section-icon graph" />
                                <div>
                                    <h2>Health Knowledge Graph</h2>
                                    <p>Visualize relationships between your health data</p>
                                </div>
                            </div>
                            <div className="section-badge">
                                <Link2 size={14} />
                                <span>Powered by Neo4j</span>
                            </div>
                        </div>

                        <div className="section-content section-content-large">
                            <HealthGraph
                                key={`graph-${syncKey}`}
                                authToken={authToken || undefined}
                                apiBaseUrl={API_BASE_URL}
                                defaultCollapsed={false}
                            />
                        </div>
                    </motion.section>

                    {/* CTA Section */}
                    <motion.section
                        className="features-cta"
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        viewport={{ once: true }}
                    >
                        <h3>See your personalized recommendations</h3>
                        <p>Your health insights are built from all these connected systems</p>
                        <button
                            className="cta-button"
                            onClick={() => navigate('/dashboard')}
                        >
                            <Sparkles size={18} />
                            Go to Dashboard
                        </button>
                    </motion.section>

                </div>
            </div>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/*  Sync step indicator sub-component                                 */
/* ------------------------------------------------------------------ */

interface SyncStepProps {
    label: string;
    active: boolean;
    done: boolean;
    icon: React.ReactNode;
}

function SyncStep({ label, active, done, icon }: SyncStepProps) {
    return (
        <div className={`sync-step ${active ? 'active' : ''} ${done ? 'done' : ''}`}>
            <span className="sync-step-icon">
                {done ? <Check size={16} /> : icon}
            </span>
            <span className="sync-step-label">{label}</span>
            {active && (
                <motion.span
                    className="sync-step-spinner"
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                >
                    <RefreshCw size={12} />
                </motion.span>
            )}
        </div>
    );
}

export default Features;
