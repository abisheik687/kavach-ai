import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { VerdictBadge } from '../components/VerdictBadge';
import { SkeletonRow } from '../components/SkeletonRow';
import { useToast } from '../hooks/useToast';
import { Toast } from '../components/Toast';

const SEVERITY_OPTIONS = ['All', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const VERDICT_OPTIONS = ['All', 'AUTHENTIC', 'DEEPFAKE', 'UNCERTAIN'];

export default function AlertsPage() {
    const navigate = useNavigate();
    const { toasts, toast, remove } = useToast();
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState(new Set());
    const [filters, setFilters] = useState({
        severity: 'All', verdict: 'All', search: '', page: 1
    });

    useEffect(() => {
        setLoading(true);
        const params = new URLSearchParams({
            page: filters.page, limit: 20,
            ...(filters.severity !== 'All' && { severity: filters.severity }),
            ...(filters.verdict !== 'All' && { verdict: filters.verdict }),
            ...(filters.search && { q: filters.search }),
        });
        fetch(`/api/v1/alerts?${params}`)
            .then(r => r.json())
            .then(d => setAlerts(d.items ?? []))
            .catch(() => toast('Failed to load alerts', 'error'))
            .finally(() => setLoading(false));
    }, [filters]);

    const toggleSelect = (id) => setSelected(s => {
        const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n;
    });

    const bulkExport = async () => {
        for (const id of selected) {
            const res = await fetch(`/api/v1/alerts/${id}/export`);
            if (!res.ok) continue;
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `kavach_evidence_${id}.json`; a.click();
            URL.revokeObjectURL(url);
        }
        toast(`${selected.size} evidence file(s) downloaded`, 'success');
        setSelected(new Set());
    };

    const setFilter = (key, value) =>
        setFilters(f => ({ ...f, [key]: value, page: 1 }));

    return (
        <div className='p-6 max-w-7xl mx-auto'>
            <div className='flex items-center justify-between mb-6'>
                <h1 className='text-2xl font-bold' style={{ color: 'var(--text-primary)' }}>
                    Alerts
                </h1>
                {selected.size > 0 && (
                    <button onClick={bulkExport}
                        className='px-4 py-2 rounded-lg text-sm font-semibold transition-all'
                        style={{ background: 'var(--cyan)', color: '#0A1628' }}>
                        ⬇ Export {selected.size} selected
                    </button>
                )}
            </div>

            {/* ── Filters ── */}
            <div className='flex flex-wrap gap-3 mb-5'>
                <input
                    type='search' placeholder='Search source URL...'
                    value={filters.search}
                    onChange={e => setFilter('search', e.target.value)}
                    className='px-3 py-2 rounded-lg text-sm flex-1 min-w-48'
                    style={{
                        background: 'var(--bg-card)', border: '1px solid var(--border)',
                        color: 'var(--text-primary)', outline: 'none'
                    }}
                />
                {[['severity', SEVERITY_OPTIONS], ['verdict', VERDICT_OPTIONS]].map(([key, opts]) => (
                    <select key={key} value={filters[key]}
                        onChange={e => setFilter(key, e.target.value)}
                        className='px-3 py-2 rounded-lg text-sm'
                        style={{
                            background: 'var(--bg-card)', border: '1px solid var(--border)',
                            color: 'var(--text-primary)', outline: 'none'
                        }}
                        aria-label={key}>
                        {opts.map(o => <option key={o} value={o}>{key}: {o}</option>)}
                    </select>
                ))}
            </div>

            {/* ── Table ── */}
            <div className='rounded-xl overflow-hidden'
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
                <table className='w-full'>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                            <th className='px-4 py-3 w-10'>
                                <input type='checkbox' aria-label='Select all'
                                    onChange={e => setSelected(
                                        e.target.checked ? new Set(alerts.map(a => a.id)) : new Set()
                                    )} />
                            </th>
                            {['Source', 'Verdict', 'Confidence', 'Severity', 'Date', 'Actions'].map(h => (
                                <th key={h} className='px-4 py-3 text-left text-xs font-semibold
                                        uppercase tracking-wider'
                                    style={{ color: 'var(--text-muted)' }}>{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {loading
                            ? Array.from({ length: 8 }).map((_, i) => (
                                <SkeletonRow key={i} cols={7} />
                            ))
                            : alerts.length === 0
                                ? (
                                    <tr><td colSpan={7} className='py-16 text-center'>
                                        <div className='flex flex-col items-center gap-3'>
                                            <span className='text-5xl'>🔍</span>
                                            <p style={{ color: 'var(--text-muted)' }}>No alerts match your filters</p>
                                            <button onClick={() => setFilters({ severity: 'All', verdict: 'All', search: '', page: 1 })}
                                                className='text-sm underline'
                                                style={{ color: 'var(--cyan)' }}>
                                                Clear filters
                                            </button>
                                        </div>
                                    </td></tr>
                                )
                                : alerts.map(alert => (
                                    <tr key={alert.id}
                                        className='transition-colors hover:bg-white/5'
                                        style={{ borderBottom: '1px solid var(--border)' }}>
                                        <td className='px-4 py-3'>
                                            <input type='checkbox' checked={selected.has(alert.id)}
                                                onChange={() => toggleSelect(alert.id)}
                                                aria-label={`Select alert ${alert.id}`} />
                                        </td>
                                        <td className='px-4 py-3 text-sm max-w-xs truncate'
                                            style={{ color: 'var(--text-secondary)' }}>
                                            {alert.source_url ?? 'File upload'}
                                        </td>
                                        <td className='px-4 py-3'>
                                            <VerdictBadge verdict={alert.verdict} size='sm' />
                                        </td>
                                        <td className='px-4 py-3 text-sm font-mono'
                                            style={{ color: 'var(--text-secondary)' }}>
                                            {alert.confidence ? `${(alert.confidence * 100).toFixed(1)}%` : '—'}
                                        </td>
                                        <td className='px-4 py-3 text-xs font-semibold'
                                            style={{
                                                color: alert.severity === 'HIGH' ? '#E63946'
                                                    : alert.severity === 'MEDIUM' ? '#F4A261' : '#2DC653'
                                            }}>
                                            {alert.severity}
                                        </td>
                                        <td className='px-4 py-3 text-xs'
                                            style={{ color: 'var(--text-muted)' }}>
                                            {new Date(alert.created_at).toLocaleString()}
                                        </td>
                                        <td className='px-4 py-3'>
                                            <div className='flex gap-2'>
                                                <button onClick={() => navigate(`/alerts/${alert.id}`)}
                                                    className='text-xs px-2 py-1 rounded transition-colors
                                           hover:bg-cyan-900/40'
                                                    style={{
                                                        color: 'var(--cyan)',
                                                        border: '1px solid var(--border)'
                                                    }}>
                                                    View
                                                </button>
                                                <button
                                                    onClick={async () => {
                                                        const r = await fetch(`/api/v1/alerts/${alert.id}/export`);
                                                        const b = await r.blob();
                                                        const u = URL.createObjectURL(b);
                                                        Object.assign(document.createElement('a'),
                                                            { href: u, download: `evidence_${alert.id}.json` }).click();
                                                        URL.revokeObjectURL(u);
                                                    }}
                                                    className='text-xs px-2 py-1 rounded transition-colors
                                     hover:bg-green-900/40'
                                                    style={{
                                                        color: 'var(--verdict-real)',
                                                        border: '1px solid var(--border)'
                                                    }}>
                                                    Export
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                        }
                    </tbody>
                </table>
            </div>
            {toasts.map(t => (
                <Toast key={t.id} message={t.message} type={t.type} onClose={() => remove(t.id)} />
            ))}
        </div>
    );
}
