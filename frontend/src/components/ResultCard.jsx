import { animate, motion, useMotionValue } from 'framer-motion';
import { useEffect, useState } from 'react';

function getBand(probability) {
  if (probability >= 0.8) return { label: 'High signal', color: '#f87171' };
  if (probability >= 0.55) return { label: 'Moderate signal', color: '#f5c842' };
  return { label: 'Low signal', color: '#34d399' };
}

/**
 * @param {{ score: { model: string, fake_prob: number, weight: number, mode: string } }} props
 */
function ResultCard({ score }) {
  const count = useMotionValue(0);
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const unsubscribe = count.on('change', (latest) => setDisplay(latest));
    const controls = animate(count, score.fake_prob * 100, { duration: 0.85, ease: 'easeOut' });
    return () => {
      controls.stop();
      unsubscribe();
    };
  }, [count, score.fake_prob]);

  const band = getBand(score.fake_prob);
  const barColor = score.fake_prob >= 0.8
    ? 'linear-gradient(90deg, #f87171, #fca5a5)'
    : score.fake_prob >= 0.55
    ? 'linear-gradient(90deg, #f5c842, #fde68a)'
    : 'linear-gradient(90deg, #34d399, #6ee7b7)';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="signal-card rounded-2xl p-5"
    >
      <div className="mb-4 flex flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="heading-font text-base" style={{ color: 'var(--text-primary)', letterSpacing: '0.04em' }}>{score.model}</p>
          <p className="label-font mt-1 text-xs uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{score.mode}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span
            className="media-badge label-font rounded-full px-3 py-1.5 text-xs font-medium"
            style={{ color: '#f5c842' }}
          >
            weight {score.weight.toFixed(2)}
          </span>
          <span
            className="media-badge label-font rounded-full px-3 py-1.5 text-xs"
            style={{ color: band.color }}
          >
            {band.label}
          </span>
        </div>
      </div>

      <div className="mb-3 flex items-end justify-between gap-3">
        <span className="label-font text-sm" style={{ color: 'var(--text-secondary)' }}>Fake probability</span>
        <span className="heading-font text-3xl" style={{ color: band.color }}>{display.toFixed(1)}%</span>
      </div>

      <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${score.fake_prob * 100}%` }}
          transition={{ duration: 0.85, ease: 'easeOut' }}
          className="h-full rounded-full"
          style={{ background: barColor }}
        />
      </div>
    </motion.div>
  );
}

export default ResultCard;
