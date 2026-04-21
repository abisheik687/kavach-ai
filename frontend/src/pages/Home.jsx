import { motion } from 'framer-motion';
import {
  ArrowRight,
  AudioLines,
  Film,
  Image as ImageIcon,
  Radar,
  Shield,
  Sparkles,
  Workflow,
} from 'lucide-react';
import { Link } from 'react-router-dom';

const mediaCards = [
  { title: 'Image Forensics', detail: 'Frame-level artifact scoring with ensemble consensus.', icon: ImageIcon },
  { title: 'Video Sampling', detail: 'Every tenth frame scored with clip-level aggregation.', icon: Film },
  { title: 'Audio Spoofing', detail: 'Waveform-backed audio verdicts with model transparency.', icon: AudioLines },
];

const trustPoints = [
  'Upload-first flow designed for reliability over gimmicks.',
  'Responsive interface tuned for desktop review and mobile submissions.',
  'No browser extension dependency. The product is now fully web-native.',
];

const workflowSteps = [
  'Drop a file or browse from any device.',
  'The backend validates size, mime type, and processing path.',
  'Results explain verdict, confidence, model scores, and media evidence.',
];

function Home() {
  return (
    <div className="scan-shell px-4 py-5 sm:px-6 lg:px-10 lg:py-8">
      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-7xl flex-col gap-8">

        {/* ── Header ── */}
        <motion.header
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col gap-4 rounded-2xl border px-5 py-4 backdrop-blur sm:flex-row sm:items-center sm:justify-between sm:px-6"
          style={{ borderColor: 'var(--border)', background: 'rgba(8,10,18,0.6)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="flex h-11 w-11 items-center justify-center rounded-xl"
              style={{
                border: '1px solid rgba(245,200,66,0.3)',
                background: 'rgba(245,200,66,0.1)',
                color: '#f5c842',
                boxShadow: '0 0 20px rgba(245,200,66,0.2)',
              }}
            >
              <Shield size={20} />
            </div>
            <div>
  <p
    className="heading-font text-base tracking-wider"
    style={{ color: '#f5c842' }}
  >
    Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques
  </p>

  <p
    className="label-font text-xs"
    style={{ color: 'var(--text-secondary)', letterSpacing: '0.08em' }}
  >
    Web forensic lab for media authenticity
  </p>
</div>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <div className="media-badge label-font inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
              <span className="status-dot" />
              Web-native experience
            </div>
            <Link
              to="/analyse"
              className="action-primary heading-font inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm"
            >
              Launch Analyse
              <ArrowRight size={14} />
            </Link>
          </div>
        </motion.header>

        {/* ── Main ── */}
        <main className="grid gap-7 lg:grid-cols-[1.1fr_0.9fr] lg:items-stretch flex-1">

          {/* Left column */}
          <section className="flex flex-col justify-between gap-8">
            <div className="space-y-7">
              <motion.div
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                className="hero-chip label-font inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold"
                style={{ color: '#f5c842', letterSpacing: '0.2em', textTransform: 'uppercase' }}
              >
                <Sparkles size={13} />
                Production-ready upload investigation
              </motion.div>

              <div className="space-y-4">
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.08 }}
                  className="section-kicker"
                >
                  Responsive · Explainable · Web-first
                </motion.p>

                <h1 className="heading-font text-5xl sm:text-6xl lg:text-[4.2rem] xl:text-[5rem]"
                  style={{ lineHeight: 1.02, color: 'var(--text-primary)' }}>
                  A stronger
                  <span
                    className="block"
                    style={{ background: 'linear-gradient(90deg, #f5c842, #e8a820, #fde68a)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}
                  >
                    deepfake detection
                  </span>
    <span style={{ color: 'var(--indigo)', WebkitTextFillColor: 'initial' }}>
  web app
</span>
</h1>

<motion.p
  initial={{ opacity: 0, y: 16 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: 0.18 }}
  className="max-w-xl text-base leading-relaxed"
  style={{ color: 'var(--text-secondary)' }}
>
  Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques
  runs as a fully web-native forensic experience. Upload media from any screen,
  inspect ensemble confidence, and review frame or waveform evidence in an interface
  designed for operational trust.
</motion.p>
</div>

<motion.div
  initial={{ opacity: 0, y: 14 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: 0.28 }}
  className="flex flex-col gap-3 sm:flex-row sm:flex-wrap"
>
<Link
                  to="/analyse"
                  className="action-primary heading-font inline-flex items-center justify-center gap-2 rounded-full px-6 py-3.5 text-sm"
                >
                  Upload Evidence
                  <ArrowRight size={15} />
                </Link>
                <div
                  className="action-secondary label-font inline-flex items-center justify-center rounded-full px-5 py-3.5 text-xs font-medium"
                  style={{ color: 'var(--text-secondary)', letterSpacing: '0.05em' }}
                >
                  JPEG · PNG · WEBP · MP4 · WEBM · WAV · MP3 · OGG
                </div>
              </motion.div>
            </div>

            {/* Media type cards */}
            <div className="grid gap-3 md:grid-cols-3">
              {mediaCards.map(({ title, detail, icon: Icon }, index) => (
                <motion.article
                  key={title}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.36 + index * 0.08 }}
                  className="signal-card rounded-2xl p-5"
                >
                  <div
                    className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl"
                    style={{ border: '1px solid rgba(245,200,66,0.18)', background: 'rgba(245,200,66,0.08)', color: '#f5c842' }}
                  >
                    <Icon size={18} />
                  </div>
                  <h2 className="heading-font text-sm" style={{ color: 'var(--text-primary)', letterSpacing: '0.06em' }}>{title}</h2>
                  <p className="label-font mt-2 text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{detail}</p>
                </motion.article>
              ))}
            </div>
          </section>

          {/* Right panel */}
          <motion.section
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="panel soft-grid relative rounded-2xl p-5 sm:p-6"
          >
            <div className="relative z-10 flex flex-col gap-6 h-full">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="section-kicker">Signal cockpit</p>
                  <h2 className="heading-font mt-2 text-2xl" style={{ color: 'var(--text-primary)' }}>Upload-first<br />mission control</h2>
                </div>
                <div className="media-badge label-font inline-flex w-fit items-center gap-2 rounded-full px-4 py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                  <Radar size={13} />
                  No extension required
                </div>
              </div>

              {/* Stats */}
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  { label: 'Surface', value: 'Web', sub: 'One interface across laptop, tablet, and phone.', color: '#f5c842' },
                  { label: 'Pipeline', value: '4+1', sub: 'Four image slots plus dedicated audio scoring.', color: 'var(--text-primary)' },
                  { label: 'Video', value: '10f', sub: 'Every tenth frame sampled for clip review.', color: 'var(--indigo)' },
                ].map(({ label, value, sub, color }) => (
                  <div key={label} className="metric-tile rounded-xl p-4">
                    <p className="label-font text-xs uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{label}</p>
                    <p className="heading-font mt-2 text-3xl" style={{ color }}>{value}</p>
                    <p className="label-font mt-2 text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{sub}</p>
                  </div>
                ))}
              </div>

              {/* Workflow + Trust */}
              <div className="grid gap-4 xl:grid-cols-2 flex-1">
                <div className="signal-card rounded-2xl p-5">
                  <div className="mb-4 flex items-center gap-2.5">
                    <Workflow size={16} style={{ color: '#f5c842' }} />
                    <p className="heading-font text-sm" style={{ color: 'var(--text-primary)', letterSpacing: '0.06em' }}>Workflow</p>
                  </div>
                  <div className="space-y-2.5">
                    {workflowSteps.map((step, index) => (
                      <div
                        key={step}
                        className="flex gap-3 rounded-xl px-4 py-3"
                        style={{ border: '1px solid var(--border-subtle)', background: 'rgba(255,255,255,0.025)' }}
                      >
                        <div
                          className="heading-font flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px]"
                          style={{ border: '1px solid rgba(245,200,66,0.22)', background: 'rgba(245,200,66,0.08)', color: '#f5c842' }}
                        >
                          0{index + 1}
                        </div>
                        <p className="label-font text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{step}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="signal-card rounded-2xl p-5">
                  <div className="mb-4 flex items-center justify-between">
                    <p className="heading-font text-sm" style={{ color: 'var(--text-primary)', letterSpacing: '0.06em' }}>Why this works better</p>
                    <span className="status-dot" />
                  </div>
                  <div className="space-y-2.5">
                    {trustPoints.map((point) => (
                      <div
                        key={point}
                        className="rounded-xl px-4 py-3"
                        style={{ border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.1)' }}
                      >
                        <p className="label-font text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{point}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.section>
        </main>

      </div>
    </div>
  );
}

export default Home;
