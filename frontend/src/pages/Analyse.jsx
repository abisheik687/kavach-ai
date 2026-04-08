import { useRef } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, AudioLines, Film, Image as ImageIcon, ShieldCheck, Upload, Workflow } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import DropZone from '../components/DropZone.jsx';
import ProgressBar from '../components/ProgressBar.jsx';
import { useDropZone } from '../hooks/useDropZone.js';

const surfaceCards = [
  { title: 'Images', detail: 'PNG, JPEG, WEBP', icon: ImageIcon },
  { title: 'Videos', detail: 'MP4, WEBM · up to 100 MB', icon: Film },
  { title: 'Audio', detail: 'WAV, MP3, OGG', icon: AudioLines },
];

const checkpoints = [
  'Client-side validation catches unsupported files before upload.',
  'Server-side validation enforces size, mime type, and processing path.',
  'Results stay in one web session, so the workflow works cleanly on any screen size.',
];

/**
 * @param {{ analysis: ReturnType<import('../hooks/useAnalysis').useAnalysis> }} props
 */
function Analyse({ analysis }) {
  const navigate = useNavigate();
  const dropzone = useDropZone();
  const inputRef = useRef(null);

  const onBrowse = () => inputRef.current?.click();

  const onFileChange = async (event) => {
    const nextFile = event.target.files?.[0];
    await dropzone.selectFile(nextFile);
    event.target.value = '';
  };

  const onSubmit = async () => {
    if (!dropzone.file) {
      dropzone.setError('Choose a supported file before starting analysis.');
      return;
    }
    try {
      await analysis.analyseFile(dropzone.file, dropzone.preview);
      navigate('/results');
    } catch {
      // Error state is already handled by the hook.
    }
  };

  const busy = analysis.status === 'uploading' || analysis.status === 'analysing';

  return (
    <div className="scan-shell px-4 py-5 sm:px-6 lg:px-10 lg:py-8">
      <div className="mx-auto max-w-7xl space-y-7">

        {/* ── Header ── */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-5 rounded-2xl border px-5 py-5 backdrop-blur sm:px-6 lg:flex-row lg:items-start lg:justify-between"
          style={{ borderColor: 'var(--border)', background: 'rgba(8,10,18,0.6)' }}
        >
          <div className="space-y-3">
            <Link
              to="/"
              className="label-font inline-flex items-center gap-2 text-sm transition"
              style={{ color: 'var(--text-secondary)' }}
              onMouseEnter={e => e.currentTarget.style.color = '#f5c842'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
            >
              <ArrowLeft size={14} />
              Back to home
            </Link>
            <div className="space-y-2">
              <p className="section-kicker">Web-first analysis console</p>
              <h1 className="heading-font text-4xl sm:text-5xl" style={{ color: 'var(--text-primary)' }}>Analyse Upload</h1>
              <p className="max-w-2xl text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                The extension path is gone and the full workflow now lives here. Upload from desktop or mobile,
                track progress in one place, and land directly in a readable forensic results view.
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:w-[26rem] lg:grid-cols-1 xl:w-[28rem] xl:grid-cols-3">
            {surfaceCards.map(({ title, detail, icon: Icon }) => (
              <div key={title} className="signal-card rounded-xl p-4">
                <div
                  className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ border: '1px solid rgba(245,200,66,0.2)', background: 'rgba(245,200,66,0.08)', color: '#f5c842' }}
                >
                  <Icon size={17} />
                </div>
                <p className="heading-font text-sm" style={{ color: 'var(--text-primary)', letterSpacing: '0.05em' }}>{title}</p>
                <p className="label-font mt-1.5 text-xs" style={{ color: 'var(--text-secondary)' }}>{detail}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* ── Main Grid ── */}
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_22rem]">

          {/* Upload area */}
          <div className="space-y-5">
            <DropZone dropzone={dropzone} disabled={busy} onBrowse={onBrowse} />
            <input ref={inputRef} type="file" className="hidden" onChange={onFileChange} />
            <ProgressBar status={analysis.status === 'idle' ? 'idle' : analysis.status} progress={analysis.progress} />

            {analysis.error ? (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="inline-error rounded-2xl px-5 py-5 sm:px-6"
              >
                <p className="heading-font text-lg" style={{ color: 'var(--text-primary)' }}>{analysis.error.title}</p>
                <p className="label-font mt-2 text-sm leading-relaxed" style={{ color: '#fecaca' }}>{analysis.error.message}</p>
                <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                  <button
                    type="button"
                    onClick={onSubmit}
                    className="action-secondary label-font rounded-full px-4 py-2.5 text-sm font-semibold transition"
                  >
                    {analysis.error.retryLabel}
                  </button>
                  <span className="data-font text-xs uppercase tracking-widest" style={{ color: 'rgba(254,202,202,0.7)' }}>
                    {analysis.error.code}
                  </span>
                </div>
              </motion.div>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <button
                type="button"
                disabled={busy}
                onClick={onSubmit}
                className="action-primary heading-font inline-flex items-center justify-center gap-2 rounded-full px-6 py-3.5 text-sm disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Upload size={15} />
                {busy ? 'Analysing…' : 'Analyse file'}
              </button>
              <button
                type="button"
                onClick={() => { analysis.reset(); dropzone.clear(); }}
                className="action-secondary label-font inline-flex items-center justify-center gap-2 rounded-full px-5 py-3.5 text-sm font-medium transition"
              >
                <ShieldCheck size={15} />
                Reset session
              </button>
            </div>
          </div>

          {/* Sidebar */}
          <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
            <div className="panel rounded-2xl p-5 sm:p-6">
              <div className="mb-4 flex items-center gap-3">
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ border: '1px solid rgba(245,200,66,0.18)', background: 'rgba(245,200,66,0.08)', color: '#f5c842' }}
                >
                  <Workflow size={17} />
                </div>
                <div>
                  <p className="section-kicker" style={{ fontSize: '0.65rem' }}>Workflow guide</p>
                  <p className="heading-font text-sm" style={{ color: 'var(--text-primary)', letterSpacing: '0.05em' }}>Why this page works better</p>
                </div>
              </div>

              <div className="space-y-2.5">
                {checkpoints.map((point, index) => (
                  <div
                    key={point}
                    className="rounded-xl px-4 py-3"
                    style={{ border: '1px solid var(--border-subtle)', background: 'rgba(255,255,255,0.025)' }}
                  >
                    <div className="mb-1.5 flex items-center gap-2">
                      <span
                        className="heading-font text-[11px] uppercase tracking-widest"
                        style={{ color: '#f5c842' }}
                      >
                        0{index + 1}
                      </span>
                    </div>
                    <p className="label-font text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{point}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="signal-card rounded-2xl p-5 sm:p-6">
              <p className="section-kicker" style={{ fontSize: '0.65rem' }}>Size limits</p>
              <div className="mt-3 grid gap-2.5 sm:grid-cols-3 xl:grid-cols-1">
                {[
                  { label: 'Images', value: '20 MB', color: '#f5c842' },
                  { label: 'Audio',  value: '20 MB', color: '#34d399' },
                  { label: 'Video',  value: '100 MB', color: 'var(--indigo)' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="metric-tile rounded-xl p-4">
                    <p className="label-font text-xs uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{label}</p>
                    <p className="heading-font mt-2 text-2xl" style={{ color }}>{value}</p>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

export default Analyse;
