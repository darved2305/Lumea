import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Brain,
    Trash2,
    RefreshCw,
    ChevronDown,
    ChevronUp,
    AlertCircle,
    Sparkles,
    Database,
    Plus,
    X,
    Search,
    Info,
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';
import './MemoryDashboard.css';

// Types matching backend schemas
interface MemoryFact {
    id: string;
    memory: string;
    created_at: string | null;
    metadata: Record<string, unknown>;
}

interface MemoryListResponse {
    facts: MemoryFact[];
    total_count: number;
    available: boolean;
    message: string | null;
}

interface MemoryDashboardProps {
    authToken?: string;
    apiBaseUrl?: string;
    defaultCollapsed?: boolean;
}

const MemoryDashboard: React.FC<MemoryDashboardProps> = ({
    authToken,
    apiBaseUrl = API_BASE_URL,
    defaultCollapsed = true,
}) => {
    const [memories, setMemories] = useState<MemoryFact[]>([]);
    const [loading, setLoading] = useState(false);
    const [deleting, setDeleting] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [collapsed, setCollapsed] = useState(defaultCollapsed);
    const [available, setAvailable] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [newMemory, setNewMemory] = useState('');
    const [adding, setAdding] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    const fetchMemories = useCallback(async () => {
        if (!authToken) {
            setError('Authentication required');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${apiBaseUrl}/api/memory/facts`, {
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch memories: ${response.status}`);
            }

            const data: MemoryListResponse = await response.json();
            setMemories(data.facts);
            setAvailable(data.available);
            if (data.message) {
                setError(data.message);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load memories');
        } finally {
            setLoading(false);
        }
    }, [authToken, apiBaseUrl]);

    useEffect(() => {
        if (!collapsed && authToken) {
            fetchMemories();
        }
    }, [collapsed, authToken, fetchMemories]);

    const handleDelete = async (memoryId: string) => {
        if (!authToken) return;

        setDeleting(memoryId);
        try {
            const response = await fetch(`${apiBaseUrl}/api/memory/facts/${memoryId}`, {
                method: 'DELETE',
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    'Content-Type': 'application/json',
                },
            });

            if (response.ok) {
                setMemories(prev => prev.filter(m => m.id !== memoryId));
            } else {
                throw new Error('Failed to delete memory');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to delete memory');
        } finally {
            setDeleting(null);
        }
    };

    const handleAdd = async () => {
        if (!authToken || !newMemory.trim()) return;

        setAdding(true);
        try {
            const response = await fetch(`${apiBaseUrl}/api/memory/facts`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ content: newMemory.trim() }),
            });

            if (response.ok) {
                setNewMemory('');
                setShowAddModal(false);
                await fetchMemories();
            } else {
                const data = await response.json();
                throw new Error(data.message || 'Failed to add memory');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to add memory');
        } finally {
            setAdding(false);
        }
    };

    const handleSearch = async () => {
        if (!authToken || !searchQuery.trim()) {
            await fetchMemories();
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(`${apiBaseUrl}/api/memory/search`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: searchQuery, limit: 20 }),
            });

            if (response.ok) {
                const data: MemoryListResponse = await response.json();
                setMemories(data.facts);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Search failed');
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    };

    return (
        <div className="memory-dashboard">
            <div
                className="memory-header"
                onClick={() => setCollapsed(!collapsed)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setCollapsed(!collapsed)}
            >
                <div className="memory-header-left">
                    <Brain size={20} className="memory-icon" />
                    <h3>Health Memory</h3>
                    <span className="memory-badge">
                        {available ? (
                            <><Database size={12} /> {memories.length}</>
                        ) : (
                            <><AlertCircle size={12} /> Offline</>
                        )}
                    </span>
                </div>
                <div className="memory-header-right">
                    {collapsed ? <ChevronDown size={20} /> : <ChevronUp size={20} />}
                </div>
            </div>

            <AnimatePresence>
                {!collapsed && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="memory-content"
                    >
                        {!available ? (
                            <div className="memory-unavailable">
                                <AlertCircle size={32} />
                                <p>Memory service is not available</p>
                                <span>Recommendations will still work, but without personalization from your preferences.</span>
                            </div>
                        ) : (
                            <>
                                <div className="memory-toolbar">
                                    <div className="memory-search">
                                        <Search size={16} />
                                        <input
                                            type="text"
                                            placeholder="Search memories..."
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                        />
                                        {searchQuery && (
                                            <button
                                                className="memory-search-clear"
                                                onClick={() => { setSearchQuery(''); fetchMemories(); }}
                                            >
                                                <X size={14} />
                                            </button>
                                        )}
                                    </div>
                                    <div className="memory-actions">
                                        <button
                                            className="memory-btn memory-btn-add"
                                            onClick={() => setShowAddModal(true)}
                                            title="Add memory"
                                        >
                                            <Plus size={16} />
                                        </button>
                                        <button
                                            className="memory-btn memory-btn-refresh"
                                            onClick={fetchMemories}
                                            disabled={loading}
                                            title="Refresh"
                                        >
                                            <RefreshCw size={16} className={loading ? 'spinning' : ''} />
                                        </button>
                                    </div>
                                </div>

                                {error && (
                                    <div className="memory-error">
                                        <AlertCircle size={16} />
                                        <span>{error}</span>
                                    </div>
                                )}

                                {loading ? (
                                    <div className="memory-loading">
                                        <RefreshCw size={24} className="spinning" />
                                        <p>Loading memories...</p>
                                    </div>
                                ) : memories.length === 0 ? (
                                    <div className="memory-empty">
                                        <Sparkles size={32} />
                                        <p>No memories yet</p>
                                        <span>Your health preferences and facts will appear here as you interact with the assistant.</span>
                                    </div>
                                ) : (
                                    <div className="memory-list">
                                        {memories.map((memory, index) => (
                                            <motion.div
                                                key={memory.id}
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: index * 0.03 }}
                                                className="memory-item"
                                            >
                                                <div className="memory-item-content">
                                                    <p>{memory.memory}</p>
                                                    {memory.created_at && (
                                                        <span className="memory-date">
                                                            {formatDate(memory.created_at)}
                                                        </span>
                                                    )}
                                                </div>
                                                <button
                                                    className="memory-delete-btn"
                                                    onClick={() => handleDelete(memory.id)}
                                                    disabled={deleting === memory.id}
                                                    title="Delete memory"
                                                >
                                                    {deleting === memory.id ? (
                                                        <RefreshCw size={14} className="spinning" />
                                                    ) : (
                                                        <Trash2 size={14} />
                                                    )}
                                                </button>
                                            </motion.div>
                                        ))}
                                    </div>
                                )}

                                <div className="memory-footer">
                                    <Info size={14} />
                                    <span>Memories help personalize your health recommendations.</span>
                                </div>
                            </>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Add Memory Modal */}
            <AnimatePresence>
                {showAddModal && (
                    <motion.div
                        className="memory-modal-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setShowAddModal(false)}
                    >
                        <motion.div
                            className="memory-modal"
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="memory-modal-header">
                                <h4>Add a Preference</h4>
                                <button onClick={() => setShowAddModal(false)}>
                                    <X size={18} />
                                </button>
                            </div>
                            <div className="memory-modal-body">
                                <textarea
                                    placeholder="e.g., I prefer vegetarian diet, I exercise in the morning, I'm allergic to penicillin..."
                                    value={newMemory}
                                    onChange={(e) => setNewMemory(e.target.value)}
                                    rows={3}
                                />
                            </div>
                            <div className="memory-modal-footer">
                                <button
                                    className="memory-btn memory-btn-cancel"
                                    onClick={() => setShowAddModal(false)}
                                >
                                    Cancel
                                </button>
                                <button
                                    className="memory-btn memory-btn-save"
                                    onClick={handleAdd}
                                    disabled={adding || !newMemory.trim()}
                                >
                                    {adding ? (
                                        <><RefreshCw size={14} className="spinning" /> Saving...</>
                                    ) : (
                                        <><Plus size={14} /> Add Preference</>
                                    )}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default MemoryDashboard;
