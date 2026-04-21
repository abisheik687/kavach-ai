import { motion } from 'framer-motion';
import { AlertTriangle, ShieldAlert, ShieldCheck } from 'lucide-react';

const MAP = {
  FAKE: {
    icon: ShieldAlert,
    border: 'rgba(248,113,113,0.35)',
    background: 'linear-gradient(135deg, rgba(248,113,113,0.14), rgba(10,12,22,0.96))',
    glow: '0 0 36px rgba(248,113,113,0.16)',
    iconColor: '#f87171',
    iconBg: 'rgba(248,113,113,0.1)',
    label: 'High forensic concern',
    description: 'The ensemble leaned toward synthetic manipulation and highlighted suspicious artifact patterns.',
    animate: { x: [0, -4, 4, -2, 0], opacity: [0.6, 1, 1, 1, 1] },
  },
  REAL: {
    icon: ShieldCheck,
    border: 'rgba(52,211,153,0.3)',
    background: 'linear-gradient(135deg, rgba(52,211,153,0.12), rgba(10,12,22,0.96))',
    glow: '0 0 32px rgba(52,211,153,0.14)',
    iconColor: '#34d399',
    iconBg: 'rgba(52,211,153,0.1)',
    label: 'Authenticity signal holds',
    description: 'The weighted models converged toward a real verdict with comparatively stable evidence patterns.',
    animate: { opacity: [0.3, 1], scale: [0.985, 1.01, 1] },
  },
  UNCERTAIN: {
    icon: AlertTriangle,
    border: 'rgba(245,200,66,0.32)',
    background: 'linear-gradient(135deg, rgba(245,200,66,0.12), rgba(10,12,22,0.96))',
    glow: '0 0 32px rgba(245,200,66,0.14)',
    iconColor: '#f5c842',
    iconBg: 'rgba(245,200,66,0.1)',
    label: 'Model disagreement detected',
    description: 'The verdict is cautious because the contributing models diverged beyond the confidence spread threshold.',
    animate: { opacity: [0.4, 1, 0.76, 1] },
  },
};

/**
 * @param {{ verdict: 'REAL'|'FAKE'|'UNCERTAIN', fakeProbability: number }} props
 */
function VerdictBanner({ verdict, fakeProbability }) {
  const config = MAP[verdict] || MAP.UNCERTAIN;
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={config.animate}
      transition={{ duration: 0.75 }}
      className="rounded-2xl border p-5 sm:p-6"
      style={{ background: config.background, borderColor: config.border, boxShadow: config.glow }}
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-4">
          <div
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl"
            style={{ border: `1px solid ${config.border}`, background: config.iconBg, color: config.iconColor }}
          >
            <Icon size={24} />
          </div>
          <div className="space-y-2.5">
            <p className="section-kicker">Verdict</p>
            <div>
              <h2 className="heading-font text-4xl sm:text-5xl" style={{ color: 'var(--text-primary)' }}>{verdict}</h2>
              <p className="label-font mt-1.5 text-sm font-medium" style={{ color: config.iconColor }}>{config.label}</p>
            </div>
            <p className="label-font max-w-xl text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{config.description}</p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:w-[18rem]">
          <div className="metric-tile rounded-xl p-4">
            <p className="label-font text-xs uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Fake probability</p>
            <p className="heading-font mt-3 text-3xl" style={{ color: 'var(--text-primary)' }}>{(fakeProbability * 100).toFixed(1)}%</p>
          </div>
          <div className="metric-tile rounded-xl p-4">
            <p className="label-font text-xs uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Review mode</p>
            <p className="heading-font mt-3 text-lg" style={{ color: 'var(--text-primary)' }}>Web forensic</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default VerdictBanner;
