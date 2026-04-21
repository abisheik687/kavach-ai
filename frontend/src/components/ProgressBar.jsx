import { motion } from 'framer-motion';

const LABELS = {
  idle:      'Awaiting evidence',
  uploading: 'Uploading file securely',
  analysing: 'Running ensemble analysis',
  done:      'Analysis complete',
  error:     'Analysis halted',
};

const STAGES = ['idle', 'uploading', 'analysing', 'done'];

/**
 * @param {{ status: string, progress: number }} props
 */
function ProgressBar({ status, progress }) {
  return (
    <div className="panel relative overflow-hidden rounded-2xl p-5 sm:p-6">
      {status === 'analysing' ? (
        <motion.div
          className="scanline"
          initial={{ x: '-100%' }}
          animate={{ x: ['-100%', '100%'] }}
          transition={{ repeat: Number.POSITIVE_INFINITY, duration: 1.3, ease: 'linear' }}
        />
      ) : null}

      <div className="relative z-10 space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="section-kicker">Processing state</p>
            <p className="heading-font mt-1.5 text-xl" style={{ color: 'var(--text-primary)' }}>{LABELS[status]}</p>
          </div>
          <div
            className="media-badge data-font inline-flex w-fit rounded-full px-4 py-2 text-sm"
            style={{ color: 'var(--text-secondary)' }}
          >
            {progress}% complete
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-4">
          {STAGES.map((stage) => {
            const active = stage === status;
            const reached = STAGES.indexOf(stage) <= STAGES.indexOf(status === 'error' ? 'analysing' : status);
            return (
              <div
                key={stage}
                className="rounded-xl px-3 py-2.5 text-center transition-all duration-200"
                style={{
                  border: active
                    ? '1px solid rgba(245,200,66,0.32)'
                    : reached
                    ? '1px solid rgba(255,255,255,0.08)'
                    : '1px solid rgba(255,255,255,0.04)',
                  background: active
                    ? 'rgba(245,200,66,0.08)'
                    : reached
                    ? 'rgba(255,255,255,0.04)'
                    : 'rgba(0,0,0,0.12)',
                }}
              >
                <p
                  className="label-font text-[11px] uppercase tracking-widest"
                  style={{ color: active ? '#f5c842' : reached ? 'var(--text-secondary)' : 'var(--text-muted)' }}
                >
                  {stage}
                </p>
              </div>
            );
          })}
        </div>

        <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg, #f5c842, #fde68a, #7b8cde)' }}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.45, ease: 'easeOut' }}
          />
        </div>
      </div>
    </div>
  );
}

export default ProgressBar;
