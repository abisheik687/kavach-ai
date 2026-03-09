import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { VerdictBadge } from '../components/VerdictBadge';
import { ConfidenceMeter } from '../components/ConfidenceMeter';
import { useToast } from '../hooks/useToast';
import { Toast } from '../components/Toast';

function ModelScoreRow({ model, score, weight }) {
    const pct = (score * 100).toFixed(1);
    const color = score >= 0.8 ? '#E63946' : score >= 0.5 ? '#F4A261' : '#2DC653';
    return (
        <tr style={{ borderBottom: '1px solid var(--border)' }}>
            <td className='px-4 py-3 text-sm font-mono' style={{ color: 'var(--text-secondary)' }}>
                {model}
            </td>
            <td className='px-4 py-3'>
                <div className='flex items-center gap-2'>
                    <div className='flex-1 h-1.5 rounded-full overflow-hidden'
                        style={{ background: 'var(--bg-primary)' }}>
                        <div className='h-full rounded-full transition-all duration-700'
                            style={{ width: `${pct}%`, background: color }} />
                    </div>
                    <span className='text-xs font-bold w-12 text-right'
                        style={{ color }}>{pct}%</span>
                </div>
            </td>
            <td className='px-4 py-3 text-sm text-center'
                style={{ color: 'var(--text-muted)' }}>
                {weight ?? '—'}
            </td>
        </tr>
    );
}

export default function ResultsPage() {
    const { alertId } = useParams();
    const navigate = useNavigate();
    const { toasts, toast, remove } = useToast();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [gradcamMode, setGradcamMode] = useState('heatmap'); // 'original'|'heatmap'
    const [exporting, setExporting] = useState(false);

    useEffect(() => {
        fetch(`/api/v1/alerts/${alertId}`)
            .then(r => r.json())
            .then(setData)
            .catch(() => toast('Failed to load result', 'error'))
            .finally(() => setLoading(false));
    }, [alertId]);

    const handleExport = async () => {
        setExporting(true);
        try {
            const res = await fetch(`/api/v1/alerts/${alertId}/export`);
            if (!res.ok) throw new Error('Export failed');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `kavach_evidence_alert_${alertId}.json`;
            a.click();
            URL.revokeObjectURL(url);
            toast('Evidence bundle downloaded!', 'success');
        } catch {
            toast('Export failed', 'error');
        } finally {
            setExporting(false);
        }
    };

    if (loading) return (
        <div className='flex items-center justify-center h-96'>
            <div className='w-8 h-8 rounded-full border-2 animate-spin'
                style={{ borderColor: 'var(--cyan)', borderTopColor: 'transparent' }} />
        </div>
    );

    const modelScores = data?.model_scores ?? {};
    const confidence = data?.confidence ? data.confidence * 100 : 0;

    return (
        <div className='p-6 max-w-5xl mx-auto'>
            <button onClick={() => navigate(-1)} className='mb-4 text-sm hover:underline'
                style={{ color: 'var(--text-muted)' }}>← Back</button>

            {/* ── Verdict banner ── */}
            <div className='rounded-xl p-6 mb-6 flex flex-col sm:flex-row
                       items-center gap-6 justify-between'
                style={{
                    background: data?.verdict === 'DEEPFAKE' ? '#2c0d10' : '#0d2c18',
                    border: `1px solid ${data?.verdict === 'DEEPFAKE' ? '#E6394633' : '#2DC65333'}`,
                }}>
                <VerdictBadge verdict={data?.verdict} size='xl' />
                <ConfidenceMeter value={confidence} size={140} />
                <div className='flex flex-col gap-2 text-sm'
                    style={{ color: 'var(--text-secondary)' }}>
                    <span>Alert ID: <strong className='font-mono'>{alertId}</strong></span>
                    <span>Faces: <strong>{data?.faces_detected ?? 0}</strong></span>
                    <span>Time: <strong>{data?.processing_time_ms}ms</strong></span>
                </div>
            </div>

            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>

                {/* ── Model scores ── */}
                <div className='rounded-xl overflow-hidden'
                    style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
                    <div className='px-4 py-3' style={{ borderBottom: '1px solid var(--border)' }}>
                        <h2 className='text-sm font-semibold uppercase tracking-wide'
                            style={{ color: 'var(--text-secondary)' }}>Model Scores</h2>
                    </div>
                    <table className='w-full'>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                {['Model', 'Score', 'Weight'].map(h => (
                                    <th key={h} className='px-4 py-2 text-left text-xs font-semibold
                                          uppercase tracking-wider'
                                        style={{ color: 'var(--text-muted)' }}>{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {Object.entries(modelScores).map(([model, score]) => (
                                <ModelScoreRow key={model} model={model}
                                    score={score} weight={data?.model_weights?.[model]} />
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* ── GradCAM viewer ── */}
                <div className='rounded-xl overflow-hidden'
                    style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
                    <div className='px-4 py-3 flex items-center justify-between'
                        style={{ borderBottom: '1px solid var(--border)' }}>
                        <h2 className='text-sm font-semibold uppercase tracking-wide'
                            style={{ color: 'var(--text-secondary)' }}>Explainability (GradCAM)</h2>
                        <div className='flex gap-1'>
                            {['original', 'heatmap'].map(m => (
                                <button key={m} onClick={() => setGradcamMode(m)}
                                    className='text-xs px-2 py-1 rounded transition-colors'
                                    style={{
                                        background: gradcamMode === m ? 'var(--cyan)' : 'var(--bg-primary)',
                                        color: gradcamMode === m ? '#0A1628' : 'var(--text-muted)',
                                    }}>
                                    {m}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className='p-4 flex items-center justify-center min-h-48'>
                        {data?.gradcam_path
                            ? <img
                                src={`/api/v1/gradcam/${gradcamMode === 'heatmap'
                                    ? data.gradcam_path : data.original_path}`}
                                alt={`GradCAM ${gradcamMode}`}
                                className='max-w-full rounded-lg object-contain max-h-64'
                                style={{ transition: 'opacity 0.3s' }}
                            />
                            : <p className='text-sm' style={{ color: 'var(--text-muted)' }}>
                                No GradCAM available
                            </p>
                        }
                    </div>
                </div>
            </div>

            {/* ── Actions ── */}
            <div className='flex gap-3 mt-6'>
                <button onClick={handleExport} disabled={exporting}
                    className='flex-1 py-2.5 rounded-lg text-sm font-semibold
                           transition-all disabled:opacity-50'
                    style={{ background: 'var(--cyan)', color: '#0A1628' }}>
                    {exporting ? 'Exporting...' : '⬇ Download Evidence Bundle'}
                </button>
                <button onClick={() => navigate('/scan')}
                    className='px-5 py-2.5 rounded-lg text-sm font-semibold
                           transition-all hover:bg-white/10'
                    style={{ border: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
                    + New Scan
                </button>
            </div>

            {toasts.map(t => (
                <Toast key={t.id} message={t.message} type={t.type} onClose={() => remove(t.id)} />
            ))}
        </div>
    );
}
