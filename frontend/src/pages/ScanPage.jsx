import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../hooks/useToast';
import { Toast } from '../components/Toast';

const STEPS = ['Face Detection', 'Model Inference', 'Ensemble', 'Report'];
const ACCEPT = 'image/jpeg,image/png,image/webp,video/mp4,video/webm,video/avi';

function ProgressPipeline({ stage }) {
    // stage: 0=idle, 1=face, 2=inference, 3=ensemble, 4=report, 5=done
    return (
        <div className='flex items-center gap-0 w-full my-6'>
            {STEPS.map((step, i) => {
                const idx = i + 1;
                const done = stage > idx;
                const active = stage === idx;
                const pending = stage < idx;
                return (
                    <div key={step} className='flex-1 flex items-center'>
                        <div className='flex flex-col items-center flex-1'>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center
                              text-xs font-bold transition-all duration-300
                              ${done ? 'bg-green-500 text-white'
                                    : active ? 'bg-cyan-500 text-black animate-pulse'
                                        : 'bg-gray-700 text-gray-500'}`}>
                                {done ? '✓' : idx}
                            </div>
                            <span className={`text-xs mt-1 text-center transition-colors
                               ${active ? 'text-cyan-400 font-semibold'
                                    : done ? 'text-green-400'
                                        : 'text-gray-600'}`}>
                                {step}
                            </span>
                        </div>
                        {i < STEPS.length - 1 && (
                            <div className='h-0.5 flex-1 mb-5 transition-all duration-500'
                                style={{ background: done ? '#2DC653' : '#1a2f4a' }} />
                        )}
                    </div>
                );
            })}
        </div>
    );
}

export default function ScanPage() {
    const navigate = useNavigate();
    const { toasts, toast, remove } = useToast();
    const fileRef = useRef();
    const [dragOver, setDragOver] = useState(false);
    const [file, setFile] = useState(null);
    const [streamUrl, setStreamUrl] = useState('');
    const [mode, setMode] = useState('file'); // 'file' | 'url'
    const [stage, setStage] = useState(0);
    const [scanning, setScanning] = useState(false);

    const handleFile = useCallback((f) => {
        if (!f) return;
        const maxMB = f.type.startsWith('video') ? 500 : 20;
        if (f.size > maxMB * 1024 * 1024) {
            toast(`File too large. Max ${maxMB}MB for ${f.type.startsWith('video') ? 'video' : 'image'}.`, 'error');
            return;
        }
        setFile(f);
        setStage(0);
    }, [toast]);

    const onDrop = useCallback((e) => {
        e.preventDefault(); setDragOver(false);
        handleFile(e.dataTransfer.files[0]);
    }, [handleFile]);

    const runScan = async () => {
        setScanning(true); setStage(1);
        try {
            const body = new FormData();
            if (mode === 'file' && file) body.append('file', file);
            else body.append('stream_url', streamUrl);

            // Simulate pipeline stage progression via WebSocket
            const ws = new WebSocket(`ws://localhost:8000/ws/scan`);
            ws.onmessage = (e) => {
                const { stage: s } = JSON.parse(e.data);
                setStage(s);
            };

            const res = await fetch('/api/v1/analyze', { method: 'POST', body });
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();
            ws.close();
            setStage(5);
            toast('Scan complete!', 'success');
            setTimeout(() => navigate(`/alerts/${data.alert_id}`), 600);
        } catch (err) {
            toast(`Scan failed: ${err.message}`, 'error');
            setStage(0);
        } finally {
            setScanning(false);
        }
    };

    return (
        <div className='p-6 max-w-3xl mx-auto'>
            <h1 className='text-2xl font-bold mb-1' style={{ color: 'var(--text-primary)' }}>
                New Scan
            </h1>
            <p className='mb-6 text-sm' style={{ color: 'var(--text-muted)' }}>
                Upload an image or video, or provide a stream URL for live detection.
            </p>

            {/* Mode toggle */}
            <div className='flex gap-2 mb-5'>
                {['file', 'url'].map(m => (
                    <button key={m} onClick={() => setMode(m)}
                        className='px-4 py-2 rounded-md text-sm font-medium transition-all'
                        style={{
                            background: mode === m ? 'var(--cyan)' : 'var(--bg-card)',
                            color: mode === m ? '#0A1628' : 'var(--text-secondary)',
                            border: '1px solid var(--border)',
                        }}>
                        {m === 'file' ? '📁 File Upload' : '🔗 URL / Stream'}
                    </button>
                ))}
            </div>

            {/* Upload zone */}
            {mode === 'file' ? (
                <div
                    onDrop={onDrop}
                    onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onClick={() => fileRef.current?.click()}
                    className='rounded-xl border-2 border-dashed cursor-pointer
                     flex flex-col items-center justify-center py-14 px-6
                     transition-all duration-200'
                    style={{
                        borderColor: dragOver ? 'var(--cyan)' : 'var(--border)',
                        background: dragOver ? 'var(--cyan-glow)' : 'var(--bg-card)',
                    }}
                >
                    <span className='text-4xl mb-3'>
                        {file ? '📄' : '⬆'}
                    </span>
                    <p className='font-medium text-sm' style={{ color: 'var(--text-primary)' }}>
                        {file ? file.name : 'Drop file here or click to browse'}
                    </p>
                    <p className='text-xs mt-1' style={{ color: 'var(--text-muted)' }}>
                        Images: JPG, PNG, WebP (max 20MB) · Videos: MP4, WebM, AVI (max 500MB)
                    </p>
                    {file && (
                        <p className='text-xs mt-2 font-mono'
                            style={{ color: 'var(--text-muted)' }}>
                            {(file.size / 1024 / 1024).toFixed(2)} MB · {file.type}
                        </p>
                    )}
                    <input ref={fileRef} type='file' accept={ACCEPT} className='hidden'
                        onChange={e => handleFile(e.target.files[0])} />
                </div>
            ) : (
                <div className='space-y-3'>
                    <input
                        type='url'
                        value={streamUrl}
                        onChange={e => setStreamUrl(e.target.value)}
                        placeholder='https://youtube.com/watch?v=...  or  rtsp://192.168.1.1:554/stream'
                        className='w-full px-4 py-3 rounded-lg text-sm font-mono'
                        style={{
                            background: 'var(--bg-card)', border: '1px solid var(--border)',
                            color: 'var(--text-primary)', outline: 'none',
                        }}
                        aria-label='Stream URL'
                    />
                    <p className='text-xs' style={{ color: 'var(--text-muted)' }}>
                        Supports: YouTube, RTSP streams, direct MP4 URLs
                    </p>
                </div>
            )}

            {/* Pipeline progress */}
            {stage > 0 && <ProgressPipeline stage={stage} />}

            {/* Scan button */}
            <button
                onClick={runScan}
                disabled={scanning || (mode === 'file' ? !file : !streamUrl)}
                className='mt-6 w-full py-3 rounded-lg font-bold text-sm tracking-wide
                   transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed'
                style={{
                    background: scanning ? 'var(--cyan-dim)' : 'var(--cyan)',
                    color: '#0A1628',
                }}
            >
                {scanning ? 'Analysing...' : '⊕  Run Deepfake Scan'}
            </button>

            {toasts.map(t => (
                <Toast key={t.id} message={t.message} type={t.type} onClose={() => remove(t.id)} />
            ))}
        </div>
    );
}
