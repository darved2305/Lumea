import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    Brain,
    Network,
    Sparkles,
    ArrowRight,
    ChevronDown,
    Database,
    Cpu,
    Zap,
    Link2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import MemoryDashboard from '../components/MemoryDashboard';
import HealthGraph from '../components/HealthGraph';
import { API_BASE_URL } from '../config/api';
import '../styles/dashboardTokens.css';
import '../styles/dashboardBase.css';
import './Features.css';

function Features() {
    const navigate = useNavigate();
    const [authToken, setAuthToken] = useState<string | null>(null);
    const [userName, setUserName] = useState('User');
    const [loading, setLoading] = useState(true);

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
    }, [navigate]);

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

export default Features;
