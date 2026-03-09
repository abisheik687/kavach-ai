import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { VerdictBadge } from '../components/VerdictBadge';
import { SkeletonRow } from '../components/SkeletonRow';

const THREAT_LEVELS = {
    LOW: { color: '#2DC653', bg: '#0d2c18', label: 'LOW RISK' },
    MEDIUM: { color: '#F4A261', bg: '#2c1f0d', label: 'MEDIUM RISK' },
    HIGH: { color: '#E63946', bg: '#2c0d10', label: 'HIGH RISK' },
    CRITICAL: { color: '#E63946', bg: '#2c0d10', label: 'CRITICAL', pulse: true },
};

function StatCard({ icon, label, value, delta, color }) {
    return (
        <div className='rounded-xl p-5 flex flex-col gap-2'
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
            <div className='flex items-center justify-between'>
                <span className='text-2xl'>{icon}</span>
                {delta != null && (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full
                           ${delta >= 0 ? 'text-red-400 bg-red-900/30'
                            : 'text-green-400 bg-green-900/30'}`}>
                        {delta >= 0 ? '+' : ''}{delta}% today
                    </span>
                )}
            </div>
            <div className='text-3xl font-bold' style={{ color: color ?? 'var(--text-primary)' }}>
                {value ?? '—'}
            </div>
            <div className='text-xs' style={{ color: 'var(--text-muted)' }}>{label}</div>
        </div>
    );
}

export default function Dashboard() {
    const navigate = useNavigate();
    const [stats, setStats] = useState(null);
    const [recent, setRecent] = useState([]);
    const [loading, setLoading] = useState(true);
    const [threatLevel, setThreatLevel] = useState('LOW');

    useEffect(() => {
        Promise.all([
            fetch('/api/v1/stats/summary').then(r => r.json()),
            fetch('/api/v1/alerts?limit=10&sort=desc').then(r => r.json()),
        ])
            .then(([s, r]) => {
                setStats(s);
                setRecent(r.items ?? []);
                // Derive threat level from recent detections
                const highCount = (r.items ?? []).filter(a => a.severity === 'HIGH').length;
                if (highCount >= 5) setThreatLevel('CRITICAL');
                else if (highCount >= 2) setThreatLevel('HIGH');
                else if (highCount >= 1) setThreatLevel('MEDIUM');
                else setThreatLevel('LOW');
            })
            .catch(() => { })
            .finally(() => setLoading(false));
    }, []);

    const tl = THREAT_LEVELS[threatLevel];

    return (
        <div className='p-6 max-w-7xl mx-auto'>

            {/* ── Threat level banner ── */}
            <div className='flex items-center justify-between mb-6 rounded-xl px-5 py-3'
                style={{ background: tl.bg, border: `1px solid ${tl.color}33` }}>
                <div className='flex items-center gap-3'>
                    <div className={`w-3 h-3 rounded-full ${tl.pulse ? 'animate-pulse' : ''}`}
                        style={{ background: tl.color }} />
                    <span className='font-bold tracking-widest text-sm'
                        style={{ color: tl.color }}>THREAT LEVEL: {tl.label}</span>
                </div>
                <button onClick={() => navigate('/scan')}
                    className='text-xs px-4 py-1.5 rounded-md font-semibold transition-all
                           hover:opacity-80'
                    style={{ background: 'var(--cyan)', color: '#0A1628' }}>
                    + New Scan
                </button>
            </div>

            {/* ── Stat cards ── */}
            <div className='grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8'>
                <StatCard icon='🔍' label='Scans Today'
                    value={stats?.scans_today} delta={stats?.scans_delta} />
                <StatCard icon='🎭' label='Deepfakes Detected'
                    value={stats?.deepfakes_today}
                    color='var(--verdict-fake)'
                    delta={stats?.deepfakes_delta} />
                <StatCard icon='🚨' label='High Risk Alerts'
                    value={stats?.high_risk_count}
                    color={stats?.high_risk_count > 0 ? '#E63946' : undefined} />
                <StatCard icon='⚡' label='Avg Inference (ms)'
                    value={stats?.avg_inference_ms} />
            </div>

            {/* ── Recent activity table ── */}
            <div className='rounded-xl overflow-hidden'
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
                <div className='px-5 py-4 flex items-center justify-between'
                    style={{ borderBottom: '1px solid var(--border)' }}>
                    <h2 className='font-semibold text-sm tracking-wide
                         uppercase' style={{ color: 'var(--text-secondary)' }}>
                        Recent Activity
                    </h2>
                    <button onClick={() => navigate('/alerts')}
                        className='text-xs hover:underline'
                        style={{ color: 'var(--cyan)' }}>View all →</button>
                </div>
                <table className='w-full'>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                            {['Source', 'Verdict', 'Confidence', 'Models', 'Time'].map(h => (
                                <th key={h} className='px-4 py-3 text-left text-xs font-semibold
                                        uppercase tracking-wider'
                                    style={{ color: 'var(--text-muted)' }}>{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {loading
                            ? Array.from({ length: 5 }).map((_, i) => (
                                <SkeletonRow key={i} cols={5} />
                            ))
                            : recent.length === 0
                                ? (
                                    <tr><td colSpan={5} className='px-4 py-12 text-center'>
                                        <div className='flex flex-col items-center gap-3'>
                                            <span className='text-4xl'>🔬</span>
                                            <p style={{ color: 'var(--text-muted)' }}>No scans yet</p>
                                            <button onClick={() => navigate('/scan')}
                                                className='text-sm px-4 py-2 rounded-md font-medium'
                                                style={{ background: 'var(--cyan)', color: '#0A1628' }}>
                                                Run your first scan
                                            </button>
                                        </div>
                                    </td></tr>
                                )
                                : recent.map(alert => (
                                    <tr key={alert.id}
                                        onClick={() => navigate(`/alerts/${alert.id}`)}
                                        className='cursor-pointer transition-colors hover:bg-white/5'
                                        style={{ borderBottom: '1px solid var(--border)' }}>
                                        <td className='px-4 py-3 text-sm max-w-xs truncate'
                                            title={alert.source_url}>
                                            {alert.source_url ?? 'File upload'}
                                        </td>
                                        <td className='px-4 py-3'>
                                            <VerdictBadge verdict={alert.verdict} size='sm' />
                                        </td>
                                        <td className='px-4 py-3 text-sm font-mono'
                                            style={{ color: 'var(--text-secondary)' }}>
                                            {alert.confidence ? `${(alert.confidence * 100).toFixed(1)}%` : '—'}
                                        </td>
                                        <td className='px-4 py-3 text-sm'
                                            style={{ color: 'var(--text-muted)' }}>
                                            {alert.models_used ?? '—'}
                                        </td>
                                        <td className='px-4 py-3 text-xs'
                                            style={{ color: 'var(--text-muted)' }}>
                                            {new Date(alert.created_at).toLocaleTimeString()}
                                        </td>
                                    </tr>
                                ))
                        }
                    </tbody>
                </table>
            </div>
        </div>
    );
}
