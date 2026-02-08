import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Network,
    RefreshCw,
    ChevronDown,
    ChevronUp,
    AlertCircle,
    Sparkles,
    ZoomIn,
    ZoomOut,
    Maximize2,
    Info,
    TrendingUp,
    GitBranch,
    AlertTriangle,
    Loader2,
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';
import './HealthGraph.css';

// Types matching backend schemas
interface GraphNode {
    id: string;
    name: string;
    type: string;
    properties: Record<string, unknown>;
}

interface GraphRelationship {
    source: string;
    relation: string;
    target: string;
    properties: Record<string, unknown>;
}

interface GraphDataResponse {
    nodes: GraphNode[];
    relationships: GraphRelationship[];
    total_nodes: number;
    total_relationships: number;
    available: boolean;
    message: string | null;
}

interface InsightResponse {
    insight_type: string;
    content: string;
    sources: string[];
    available: boolean;
    message: string | null;
}

type InsightType = 'temporal' | 'relationships' | 'contradictions';

const INSIGHT_BUTTONS: { type: InsightType; icon: typeof TrendingUp; label: string; description: string }[] = [
    { type: 'temporal', icon: TrendingUp, label: 'Timeline Analysis', description: 'How have my metrics changed?' },
    { type: 'relationships', icon: GitBranch, label: 'Health Connections', description: 'What\'s connected in my health data?' },
    { type: 'contradictions', icon: AlertTriangle, label: 'Data Conflicts', description: 'Any inconsistencies in my records?' },
];

interface HealthGraphProps {
    authToken?: string;
    apiBaseUrl?: string;
    defaultCollapsed?: boolean;
}

// Node type colors - using dashboard theme palette
const nodeColors: Record<string, string> = {
    condition: '#c85a54',     // dash-danger (red)
    metric: '#7a9cc6',        // dash-info (blue)
    medication: '#6b9175',    // dash-accent (green)
    recommendation: '#d9a962', // dash-warning (amber)
    user: '#4a7c59',          // dash-accent-dark (dark green)
    entity: '#999999',        // dash-text-muted (gray)
};

const normalizeNodeId = (value: string): string => value.trim().toLowerCase().replace(/\s+/g, '_');

const HealthGraph: React.FC<HealthGraphProps> = ({
    authToken,
    apiBaseUrl = API_BASE_URL,
    defaultCollapsed = true,
}) => {
    const [graphData, setGraphData] = useState<GraphDataResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [syncNotice, setSyncNotice] = useState<string | null>(null);
    const [collapsed, setCollapsed] = useState(defaultCollapsed);
    const [available, setAvailable] = useState(true);
    const [zoom, setZoom] = useState(1);
    const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
    const svgRef = useRef<SVGSVGElement>(null);

    // Insights state
    const [insightLoading, setInsightLoading] = useState(false);
    const [insightContent, setInsightContent] = useState<string | null>(null);
    const [insightSources, setInsightSources] = useState<string[]>([]);
    const [activeInsightType, setActiveInsightType] = useState<InsightType | null>(null);
    const [insightError, setInsightError] = useState<string | null>(null);

    const fetchGraphData = useCallback(async () => {
        if (!authToken) {
            setError('Authentication required');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${apiBaseUrl}/api/graph/relationships?limit=30`, {
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch graph data: ${response.status}`);
            }

            const data: GraphDataResponse = await response.json();
            setGraphData(data);
            setAvailable(data.available);
            if (data.message) {
                setError(data.message);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load graph data');
        } finally {
            setLoading(false);
        }
    }, [authToken, apiBaseUrl]);

    // Generate AI insight from graph data
    const generateInsight = useCallback(async (insightType: InsightType) => {
        if (!authToken) {
            setInsightError('Authentication required');
            return;
        }

        setInsightLoading(true);
        setInsightError(null);
        setInsightContent(null);
        setActiveInsightType(insightType);

        try {
            const response = await fetch(`${apiBaseUrl}/api/graph/insights`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ insight_type: insightType, context_limit: 10 }),
            });

            if (!response.ok) {
                throw new Error(`Failed to generate insight: ${response.status}`);
            }

            const data: InsightResponse = await response.json();

            if (!data.available) {
                throw new Error(data.message || 'Service not available');
            }

            if (data.message && !data.content) {
                throw new Error(data.message);
            }

            if (!data.content || data.content.trim() === '') {
                setInsightError('No insight generated. Try adding more health data.');
                return;
            }

            setInsightContent(data.content);
            setInsightSources(data.sources || []);
        } catch (err) {
            setInsightError(err instanceof Error ? err.message : 'Failed to generate insight');
        } finally {
            setInsightLoading(false);
        }
    }, [authToken, apiBaseUrl]);

    const syncProfileToGraph = useCallback(async () => {
        if (!authToken) {
            setError('Authentication required');
            return;
        }

        setSyncing(true);
        setError(null);
        setSyncNotice(null);

        try {
            const response = await fetch(`${apiBaseUrl}/api/profile/sync-to-memory`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`Profile sync failed: ${response.status}`);
            }

            const payload = await response.json().catch(() => null);
            if (payload?.success === false) {
                throw new Error(payload?.message || 'Profile sync failed');
            }
            const syncedFacts = payload?.synced?.facts_synced;
            if (typeof syncedFacts === 'number') {
                setSyncNotice(`Synced ${syncedFacts} facts from your profile. Refreshing graph...`);
            } else {
                setSyncNotice('Profile sync completed. Refreshing graph...');
            }

            await fetchGraphData();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to sync profile data');
        } finally {
            setSyncing(false);
        }
    }, [authToken, apiBaseUrl, fetchGraphData]);

    useEffect(() => {
        if (!collapsed && authToken) {
            fetchGraphData();
        }
    }, [collapsed, authToken, fetchGraphData]);

    // Simple force-directed layout calculation (simplified)
    const calculateLayout = useCallback((nodes: GraphNode[]) => {
        const width = 600;
        const height = 400;
        const centerX = width / 2;
        const centerY = height / 2;

        // Position nodes in a circle or hierarchical layout
        const nodePositions: Record<string, { x: number; y: number }> = {};
        const nodeCount = nodes.length;

        if (nodeCount === 0) return nodePositions;

        // Group nodes by type
        const nodesByType: Record<string, GraphNode[]> = {};
        nodes.forEach(node => {
            if (!nodesByType[node.type]) {
                nodesByType[node.type] = [];
            }
            nodesByType[node.type].push(node);
        });

        // Position nodes by type in concentric circles
        const types = Object.keys(nodesByType);
        let currentRadius = 80;

        types.forEach((type, typeIndex) => {
            const typeNodes = nodesByType[type];
            const angleStep = (2 * Math.PI) / typeNodes.length;
            const offsetAngle = (typeIndex * Math.PI) / types.length;

            typeNodes.forEach((node, nodeIndex) => {
                const angle = offsetAngle + nodeIndex * angleStep;
                nodePositions[node.id] = {
                    x: centerX + currentRadius * Math.cos(angle),
                    y: centerY + currentRadius * Math.sin(angle),
                };
            });

            currentRadius += 60;
        });

        return nodePositions;
    }, []);

    const nodePositions = useMemo(
        () => (graphData ? calculateLayout(graphData.nodes) : {}),
        [graphData, calculateLayout]
    );

    const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.2, 2));
    const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.2, 0.5));
    const handleResetZoom = () => setZoom(1);

    return (
        <div className="health-graph">
            <div
                className="health-graph-header"
                onClick={() => setCollapsed(!collapsed)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setCollapsed(!collapsed)}
            >
                <div className="health-graph-header-left">
                    <Network size={20} className="health-graph-icon" />
                    <h3>Health Knowledge Graph</h3>
                    <span className="health-graph-badge">
                        {available ? (
                            <>{graphData?.total_nodes || 0} nodes</>
                        ) : (
                            <><AlertCircle size={12} /> Offline</>
                        )}
                    </span>
                </div>
                <div className="health-graph-header-right">
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
                        className="health-graph-content"
                    >
                        {!available ? (
                            <div className="health-graph-unavailable">
                                <AlertCircle size={32} />
                                <p>Knowledge graph service is not available</p>
                                <span>Neo4j connection is required for relationship visualization.</span>
                            </div>
                        ) : loading ? (
                            <div className="health-graph-loading">
                                <RefreshCw size={24} className="spinning" />
                                <p>Loading health relationships...</p>
                            </div>
                        ) : !graphData || graphData.nodes.length === 0 ? (
                            <div className="health-graph-empty">
                                <Sparkles size={32} />
                                <p>No graph data for your account yet</p>
                                <span>
                                    This graph is user-scoped. Sync your profile data or upload reports to generate
                                    relationships.
                                </span>
                                {syncNotice && (
                                    <span className="health-graph-empty-note">{syncNotice}</span>
                                )}
                                <button
                                    className="health-graph-empty-sync"
                                    onClick={syncProfileToGraph}
                                    disabled={syncing || loading}
                                >
                                    {syncing ? <RefreshCw size={14} className="spinning" /> : <Sparkles size={14} />}
                                    <span>{syncing ? 'Syncing...' : 'Sync Profile Data'}</span>
                                </button>
                            </div>
                        ) : (
                            <>
                                <div className="health-graph-toolbar">
                                    <div className="health-graph-controls">
                                        <button onClick={handleZoomOut} title="Zoom out">
                                            <ZoomOut size={16} />
                                        </button>
                                        <span className="zoom-level">{Math.round(zoom * 100)}%</span>
                                        <button onClick={handleZoomIn} title="Zoom in">
                                            <ZoomIn size={16} />
                                        </button>
                                        <button onClick={handleResetZoom} title="Reset zoom">
                                            <Maximize2 size={16} />
                                        </button>
                                    </div>
                                    <div className="health-graph-actions">
                                        <button
                                            className="health-graph-sync"
                                            onClick={syncProfileToGraph}
                                            disabled={syncing || loading}
                                            title="Sync profile into per-user graph"
                                        >
                                            {syncing ? <RefreshCw size={14} className="spinning" /> : <Sparkles size={14} />}
                                            <span>{syncing ? 'Syncing...' : 'Sync Profile'}</span>
                                        </button>
                                        <button
                                            className="health-graph-refresh"
                                            onClick={fetchGraphData}
                                            title="Refresh"
                                        >
                                            <RefreshCw size={16} />
                                        </button>
                                    </div>
                                </div>

                                {syncNotice && (
                                    <div className="health-graph-note">
                                        <Info size={14} />
                                        <span>{syncNotice}</span>
                                    </div>
                                )}

                                {/* AI Insights Panel */}
                                <div className="health-graph-insights">
                                    <div className="insights-header">
                                        <Sparkles size={16} className="insights-icon" />
                                        <span className="insights-title">AI-Powered Insights</span>
                                    </div>
                                    <div className="insights-buttons">
                                        {INSIGHT_BUTTONS.map(({ type, icon: Icon, label, description }) => (
                                            <button
                                                key={type}
                                                className={`insight-button insight-button-${type} ${activeInsightType === type ? 'active' : ''}`}
                                                onClick={() => generateInsight(type)}
                                                disabled={insightLoading}
                                                title={description}
                                            >
                                                {insightLoading && activeInsightType === type ? (
                                                    <Loader2 size={16} className="spinning" />
                                                ) : (
                                                    <Icon size={16} />
                                                )}
                                                <span>{label}</span>
                                            </button>
                                        ))}
                                    </div>

                                    <AnimatePresence>
                                        {(insightContent || insightLoading || insightError) && (
                                            <motion.div
                                                initial={{ height: 0, opacity: 0 }}
                                                animate={{ height: 'auto', opacity: 1 }}
                                                exit={{ height: 0, opacity: 0 }}
                                                transition={{ duration: 0.2 }}
                                                className="insights-content"
                                            >
                                                {insightLoading ? (
                                                    <div className="insights-loading">
                                                        <Loader2 size={20} className="spinning" />
                                                        <span>Analyzing your health data...</span>
                                                    </div>
                                                ) : insightError ? (
                                                    <div className="insights-error">
                                                        <AlertCircle size={16} />
                                                        <span>{insightError}</span>
                                                    </div>
                                                ) : insightContent && (
                                                    <>
                                                        <div className="insights-text">
                                                            {insightContent.split('\n').filter(line => line.trim()).map((line, i) => (
                                                                <p key={i}>{line}</p>
                                                            ))}
                                                        </div>
                                                        {insightSources.length > 0 && (
                                                            <details className="insights-sources">
                                                                <summary>
                                                                    <Info size={12} />
                                                                    <span>{insightSources.length} facts used</span>
                                                                </summary>
                                                                <ul>
                                                                    {insightSources.map((source, i) => (
                                                                        <li key={i}>{source}</li>
                                                                    ))}
                                                                </ul>
                                                            </details>
                                                        )}
                                                    </>
                                                )}
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>

                                {error && (
                                    <div className="health-graph-error">
                                        <AlertCircle size={16} />
                                        <span>{error}</span>
                                    </div>
                                )}

                                <div className="health-graph-canvas-wrapper">
                                    <svg
                                        ref={svgRef}
                                        className="health-graph-canvas"
                                        viewBox="0 0 600 400"
                                        style={{ transform: `scale(${zoom})` }}
                                    >
                                        {/* Relationship lines */}
                                        <g className="relationships">
                                            {graphData.relationships.map((rel, index) => {
                                                const sourcePos = nodePositions[normalizeNodeId(rel.source)];
                                                const targetPos = nodePositions[normalizeNodeId(rel.target)];

                                                if (!sourcePos || !targetPos) return null;

                                                return (
                                                    <g key={`rel-${index}`} className="relationship">
                                                        <line
                                                            x1={sourcePos.x}
                                                            y1={sourcePos.y}
                                                            x2={targetPos.x}
                                                            y2={targetPos.y}
                                                            className="relationship-line"
                                                        />
                                                        <text
                                                            x={(sourcePos.x + targetPos.x) / 2}
                                                            y={(sourcePos.y + targetPos.y) / 2 - 5}
                                                            className="relationship-label"
                                                        >
                                                            {rel.relation}
                                                        </text>
                                                    </g>
                                                );
                                            })}
                                        </g>

                                        {/* Nodes */}
                                        <g className="nodes">
                                            {graphData.nodes.map((node) => {
                                                const pos = nodePositions[node.id];
                                                if (!pos) return null;

                                                const isHovered = hoveredNode?.id === node.id;

                                                return (
                                                    <g
                                                        key={node.id}
                                                        className="node"
                                                        transform={`translate(${pos.x}, ${pos.y})`}
                                                        onMouseEnter={() => setHoveredNode(node)}
                                                        onMouseLeave={() => setHoveredNode(null)}
                                                    >
                                                        <circle
                                                            r={isHovered ? 38 : 34}
                                                            fill={nodeColors[node.type] || nodeColors.entity}
                                                            className="node-circle"
                                                        />
                                                        <text
                                                            y={5}
                                                            textAnchor="middle"
                                                            className="node-label"
                                                        >
                                                            {node.name.length > 14
                                                                ? node.name.slice(0, 12) + '...'
                                                                : node.name}
                                                        </text>
                                                    </g>
                                                );
                                            })}
                                        </g>
                                    </svg>

                                    {/* Tooltip */}
                                    {hoveredNode && (
                                        <div className="health-graph-tooltip">
                                            <strong>{hoveredNode.name}</strong>
                                            <span className="tooltip-type">{hoveredNode.type}</span>
                                        </div>
                                    )}
                                </div>

                                {/* Legend */}
                                <div className="health-graph-legend">
                                    {Object.entries(nodeColors).slice(0, 5).map(([type, color]) => (
                                        <div key={type} className="legend-item">
                                            <span
                                                className="legend-color"
                                                style={{ backgroundColor: color }}
                                            />
                                            <span className="legend-label">{type}</span>
                                        </div>
                                    ))}
                                </div>

                                <div className="health-graph-footer">
                                    <Info size={14} />
                                    <span>
                                        Showing {graphData.total_nodes} entities and {graphData.total_relationships} relationships
                                    </span>
                                </div>
                            </>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default HealthGraph;
