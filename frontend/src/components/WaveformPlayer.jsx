import { motion } from 'framer-motion';

/**
 * @param {{ waveform: number[], url: string, verdict: string }} props
 */
function WaveformPlayer({ waveform, url, verdict }) {
  const barColor =
    verdict === 'FAKE' ? 'rgba(248,113,113,0.75)' :
    verdict === 'REAL' ? 'rgba(52,211,153,0.75)' :
    'rgba(245,200,66,0.75)';

  const badgeColor =
    verdict === 'FAKE' ? '#f87171' :
    verdict === 'REAL' ? '#34d399' :
    '#f5c842';

  return (
    <div className="panel rounded-2xl p-5 sm:p-6">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="section-kicker" style={{ fontSize: '0.65rem' }}>Audio evidence</p>
          <p className="heading-font mt-1.5 text-xl" style={{ color: 'var(--text-primary)' }}>Waveform review</p>
        </div>
        <div
          className="media-badge label-font rounded-full px-4 py-1.5 text-xs uppercase tracking-wider"
          style={{ color: badgeColor, borderColor: `${badgeColor}30` }}
        >
          {verdict}
        </div>
      </div>
      <div
        className="mb-5 flex h-28 items-end gap-0.5 overflow-hidden rounded-xl p-4 sm:h-32"
        style={{ background: 'rgba(0,0,0,0.2)' }}
      >
        {waveform.map((value, index) => (
          <motion.div
            key={`${index}-${value}`}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: `${Math.max(10, value * 180)}px`, opacity: 1 }}
            transition={{ delay: index * 0.008, duration: 0.22 }}
            className="flex-1 rounded-sm"
            style={{ background: barColor }}
          />
        ))}
      </div>
      {url ? <audio controls src={url} className="w-full" /> : null}
    </div>
  );
}

export default WaveformPlayer;
