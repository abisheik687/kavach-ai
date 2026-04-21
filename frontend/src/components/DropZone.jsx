import { motion } from 'framer-motion';
import { AudioLines, Film, Image as ImageIcon, RefreshCcw, Sparkles, UploadCloud, X } from 'lucide-react';

function getIcon(kind) {
  if (kind === 'video') return Film;
  if (kind === 'audio') return AudioLines;
  return ImageIcon;
}

function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

/**
 * @param {{
 *   dropzone: ReturnType<import('../hooks/useDropZone').useDropZone>,
 *   disabled: boolean,
 *   onBrowse: () => void,
 * }} props
 */
function DropZone({ dropzone, disabled, onBrowse }) {
  const Icon = getIcon(dropzone.preview?.kind);
  const empty = !dropzone.file;

  return (
    <div className="space-y-4">
      <motion.div
        onDragOver={disabled ? undefined : dropzone.onDragOver}
        onDragLeave={disabled ? undefined : dropzone.onDragLeave}
        onDrop={disabled ? undefined : dropzone.onDrop}
        whileHover={disabled ? undefined : { scale: 1.005 }}
        animate={
          dropzone.file
            ? { scale: [1, 1.01, 1], borderColor: ['rgba(245,200,66,0.2)', '#f5c842', 'rgba(245,200,66,0.2)'] }
            : dropzone.isDragging
            ? { scale: 1.012, borderColor: '#f5c842' }
            : { scale: 1, borderColor: 'rgba(245,200,66,0.18)' }
        }
        transition={{ duration: 0.4 }}
        className="panel relative overflow-hidden rounded-2xl border border-dashed px-5 py-6 sm:px-6 sm:py-8"
      >
        {dropzone.file ? (
          <div className="drop-burst" aria-hidden="true">
            <span /><span /><span /><span /><span />
          </div>
        ) : null}

        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
            <div
              className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl"
              style={{
                border: '1px solid rgba(245,200,66,0.22)',
                background: 'rgba(245,200,66,0.08)',
                color: '#f5c842',
                boxShadow: '0 0 20px rgba(245,200,66,0.12)',
              }}
            >
              <Icon size={24} />
            </div>

            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className="hero-chip label-font inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest"
                  style={{ color: '#f5c842' }}
                >
                  <Sparkles size={12} />
                  {empty ? 'Ready for upload' : 'Evidence staged'}
                </span>
                <span
                  className="media-badge label-font rounded-full px-3 py-1.5 text-[11px] uppercase tracking-wider"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  Drag and drop or browse
                </span>
              </div>

              <div>
                <p className="heading-font text-2xl sm:text-3xl" style={{ color: 'var(--text-primary)' }}>
                  {empty ? 'Upload forensic evidence' : 'Evidence locked in'}
                </p>
                <p className="label-font mt-2 max-w-xl text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                  Submit one media file and inspect the result in a web-native review flow built for large screens and mobile uploads alike.
                </p>
              </div>

              {dropzone.file ? (
                <div className="flex flex-wrap gap-2 text-sm">
                  <span className="media-badge label-font rounded-full px-3 py-1.5 text-xs" style={{ color: 'var(--text-primary)' }}>{dropzone.file.name}</span>
                  <span className="media-badge data-font rounded-full px-3 py-1.5 text-xs" style={{ color: 'var(--text-secondary)' }}>{formatBytes(dropzone.file.size)}</span>
                  <span className="media-badge label-font rounded-full px-3 py-1.5 text-xs uppercase" style={{ color: '#f5c842' }}>{dropzone.preview?.kind}</span>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {['JPEG / PNG / WEBP', 'MP4 / WEBM', 'WAV / MP3 / OGG'].map((fmt) => (
                    <span key={fmt} className="media-badge label-font rounded-full px-3 py-1.5 text-xs uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>{fmt}</span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-2.5 sm:flex-row lg:flex-col lg:items-stretch">
            <button
              type="button"
              disabled={disabled}
              onClick={onBrowse}
              className="action-primary label-font inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40"
            >
              <UploadCloud size={15} />
              Browse file
            </button>
            {dropzone.file ? (
              <>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => dropzone.clear()}
                  className="action-secondary label-font inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm transition disabled:opacity-40"
                >
                  <X size={15} />
                  Clear
                </button>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={onBrowse}
                  className="action-secondary label-font inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm transition disabled:opacity-40"
                >
                  <RefreshCcw size={15} />
                  Replace
                </button>
              </>
            ) : null}
          </div>
        </div>
      </motion.div>

      {dropzone.error ? (
        <div className="inline-error rounded-2xl px-4 py-3 text-sm leading-relaxed">{dropzone.error}</div>
      ) : null}

      {dropzone.preview?.kind === 'image' ? (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="panel overflow-hidden rounded-2xl p-3">
          <img src={dropzone.preview.url} alt="Selected upload preview" className="max-h-[400px] w-full rounded-xl object-contain" style={{ background: 'rgba(0,0,0,0.2)' }} />
        </motion.div>
      ) : null}

      {dropzone.preview?.kind === 'video' ? (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="panel overflow-hidden rounded-2xl p-4">
          {dropzone.preview.thumbnailUrl ? (
            <img src={dropzone.preview.thumbnailUrl} alt="Video thumbnail" className="aspect-video w-full rounded-xl object-cover" />
          ) : (
            <video src={dropzone.preview.url} controls className="aspect-video w-full rounded-xl object-cover" />
          )}
        </motion.div>
      ) : null}

      {dropzone.preview?.kind === 'audio' ? (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="panel rounded-2xl p-4">
          <div className="audio-bars mb-4 h-24 rounded-xl p-4" style={{ background: 'rgba(0,0,0,0.2)' }}>
            {dropzone.preview.waveform.map((value, index) => (
              <span
                key={`${index}-${value}`}
                style={{ height: `${Math.max(10, value * 160)}px`, background: 'rgba(245,200,66,0.7)' }}
              />
            ))}
          </div>
          <audio controls src={dropzone.preview.url} className="w-full" />
        </motion.div>
      ) : null}
    </div>
  );
}

export default DropZone;
