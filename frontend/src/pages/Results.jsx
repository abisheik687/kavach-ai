import { motion } from 'framer-motion';
import { ArrowLeft, AudioLines, Clock3, FileVideo2, Image as ImageIcon, RotateCcw, Shield, Waves } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import ResultCard from '../components/ResultCard.jsx';
import VerdictBanner from '../components/VerdictBanner.jsx';
import VideoFrameGrid from '../components/VideoFrameGrid.jsx';
import WaveformPlayer from '../components/WaveformPlayer.jsx';

function ProbabilityRing({ probability }) {
  const radius = 72;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - circumference * probability;

  const ringColor = probability >= 0.8 ? ['#f87171', '#fca5a5'] :
                    probability >= 0.55 ? ['#f5c842', '#fde68a'] :
                    ['#34d399', '#6ee7b7'];

  return (
    <div
      className="panel relative flex w-full flex-col items-center rounded-2xl p-5 sm:p-6"
      style={{ position: 'relative' }}
    >
      {/* subtle orbital ring */}
      <div
        style={{
          position: 'absolute',
          inset: '12%',
          border: '1px dashed rgba(245,200,66,0.1)',
          borderRadius: '999px',
          pointerEvents: 'none',
        }}
      />
      <svg viewBox="0 0 180 180" className="h-52 w-52 sm:h-60 sm:w-60">
        <circle cx="90" cy="90" r={radius} stroke="rgba(255,255,255,0.06)" strokeWidth="10" fill="none" />
        <motion.circle
          cx="90" cy="90" r={radius}
          stroke="url(#ringGradient)"
          strokeWidth="10"
          fill="none"
          strokeLinecap="round"
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut' }}
          strokeDasharray={circumference}
          transform="rotate(-90 90 90)"
        />
        <defs>
          <linearGradient id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={ringColor[0]} />
            <stop offset="100%" stopColor={ringColor[1]} />
          </linearGradient>
        </defs>
        <text x="90" y="78" textAnchor="middle" fill="var(--text-secondary)" fontSize="11" fontFamily="DM Sans" letterSpacing="2">FAKE PROBABILITY</text>
        <text x="90" y="112" textAnchor="middle" fill={ringColor[0]} fontSize="30" fontFamily="Syne" fontWeight="700">
          {(probability * 100).toFixed(1)}%
        </text>
      </svg>
      <p className="label-font text-center text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        Weighted ensemble signal across the analysed upload.
      </p>
    </div>
  );
}

function AssetPreviewCard({ asset }) {
  if (!asset) return null;
  return (
    <div className="panel rounded-2xl p-5 sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="section-kicker" style={{ fontSize: '0.65rem' }}>Uploaded media</p>
          <p className="heading-font mt-1.5 text-lg" style={{ color: 'var(--text-primary)' }}>{asset.name}</p>
        </div>
        <div className="media-badge label-font rounded-full px-3 py-1.5 text-xs uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
          {asset.fileType}
        </div>
      </div>
      {asset.fileType === 'image' ? (
        <img src={asset.previewUrl} alt={asset.name} className="max-h-[300px] w-full rounded-xl object-contain" style={{ background: 'rgba(0,0,0,0.2)' }} />
      ) : null}
      {asset.fileType === 'video' ? (
        <img src={asset.thumbnailUrl || asset.previewUrl} alt={asset.name} className="aspect-video w-full rounded-xl object-cover" />
      ) : null}
      {asset.fileType === 'audio' ? (
        <div className="space-y-4">
          <div className="audio-bars h-28 rounded-xl p-4" style={{ background: 'rgba(0,0,0,0.2)' }}>
            {(asset.waveform || []).map((value, index) => (
              <span key={`${index}-${value}`} style={{ height: `${Math.max(10, value * 160)}px`, background: 'rgba(245,200,66,0.65)' }} />
            ))}
          </div>
          <audio controls src={asset.previewUrl} className="w-full" />
        </div>
      ) : null}
    </div>
  );
}

/**
 * @param {{ analysis: ReturnType<import('../hooks/useAnalysis').useAnalysis> }} props
 */
function Results({ analysis }) {
  const navigate = useNavigate();
  const { result, asset } = analysis;

  if (!result) {
    return (
      <div className="scan-shell flex items-center justify-center px-4 py-6 sm:px-6 lg:px-10">
        <div className="panel max-w-md rounded-2xl p-8 text-center">
          <Shield size={32} style={{ color: 'var(--accent)', margin: '0 auto 1rem' }} />
          <p className="heading-font text-2xl" style={{ color: 'var(--text-primary)' }}>No result loaded</p>
          <p className="label-font mt-3 text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Start a new upload to generate a deepfake analysis result.
          </p>
          <Link
            to="/analyse"
            className="action-primary heading-font mt-6 inline-flex rounded-full px-6 py-3 text-sm transition"
            style={{ display: 'inline-flex' }}
          >
            Go to Analyse
          </Link>
        </div>
      </div>
    );
  }

  const metaCards = [
    { label: 'File type',        value: result.file_type,                              icon: result.file_type === 'video' ? FileVideo2 : result.file_type === 'audio' ? AudioLines : ImageIcon, color: 'var(--indigo)' },
    { label: 'Confidence',       value: `${(result.overall_confidence * 100).toFixed(1)}%`, icon: Shield,   color: '#f5c842' },
    { label: 'Processing time',  value: `${(result.processing_time_ms / 1000).toFixed(2)}s`, icon: Clock3,   color: '#34d399' },
  ];

  return (
    <div className="scan-shell px-4 py-5 sm:px-6 lg:px-10 lg:py-8">
      <div className="mx-auto max-w-7xl space-y-7">

        {/* ── Header ── */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-4 rounded-2xl border px-5 py-5 backdrop-blur sm:flex-row sm:items-center sm:justify-between sm:px-6"
          style={{ borderColor: 'var(--border)', background: 'rgba(8,10,18,0.6)' }}
        >
          <div>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="label-font mb-3 inline-flex items-center gap-2 text-sm transition"
              style={{ color: 'var(--text-secondary)', background: 'none', border: 'none', padding: 0 }}
              onMouseEnter={e => e.currentTarget.style.color = '#f5c842'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
            >
              <ArrowLeft size={14} />
              Back
            </button>
            <p className="section-kicker">Forensic output</p>
            <h1 className="heading-font mt-1.5 text-4xl sm:text-5xl" style={{ color: 'var(--text-primary)' }}>Detection Results</h1>
          </div>
          <button
            type="button"
            onClick={() => { analysis.reset(); navigate('/analyse'); }}
            className="action-secondary heading-font inline-flex items-center justify-center gap-2 rounded-full px-5 py-3.5 text-sm transition"
          >
            <RotateCcw size={15} />
            Analyse another
          </button>
        </motion.div>

        {/* ── Verdict Banner ── */}
        <VerdictBanner verdict={result.verdict} fakeProbability={result.fake_probability} />

        {/* ── Main Grid ── */}
        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">

          {/* Left: ring + preview */}
          <div className="space-y-5">
            <ProbabilityRing probability={result.fake_probability} />
            <AssetPreviewCard asset={asset} />
          </div>

          {/* Right: meta + model breakdown */}
          <div className="space-y-5">

            {/* Meta cards */}
            <div className="grid gap-3 sm:grid-cols-3">
              {metaCards.map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="signal-card rounded-xl p-4">
                  <div
                    className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
                    style={{ border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.04)', color }}
                  >
                    <Icon size={17} />
                  </div>
                  <p className="label-font text-xs uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{label}</p>
                  <p className="heading-font mt-2 text-2xl" style={{ color: 'var(--text-primary)' }}>{value}</p>
                </div>
              ))}
            </div>



            {/* Model breakdown */}
            <div className="panel rounded-2xl p-5 sm:p-6">
              <div className="flex items-center justify-between gap-3 mb-5">
                <div>
                  <p className="section-kicker" style={{ fontSize: '0.65rem' }}>Model breakdown</p>
                  <p className="heading-font mt-1.5 text-xl" style={{ color: 'var(--text-primary)' }}>Confidence by model</p>
                </div>
                <div
                  className="media-badge data-font rounded-full px-3 py-1.5 text-xs uppercase tracking-wider"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {result.model_scores.length} scores
                </div>
              </div>
              <div className="grid gap-3 lg:grid-cols-2">
                {result.model_scores.map((score, index) => (
                  <motion.div
                    key={`${score.model}-${score.mode}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.07 }}
                  >
                    <ResultCard score={score} />
                  </motion.div>
                ))}
              </div>
            </div>

          </div>
        </div>

        {/* ── Video frames ── */}
        {result.video_frame_previews?.length ? (
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <FileVideo2 size={18} style={{ color: '#f5c842' }} />
              <h2 className="heading-font text-2xl" style={{ color: 'var(--text-primary)' }}>Sampled video frames</h2>
            </div>
            <VideoFrameGrid frames={result.video_frame_previews} />
          </section>
        ) : null}

        {/* ── Audio result ── */}
        {result.audio_result ? (
          <section className="space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <Waves size={18} style={{ color: '#f5c842' }} />
                <h2 className="heading-font text-2xl" style={{ color: 'var(--text-primary)' }}>Audio result</h2>
              </div>
              <span
                className="media-badge label-font rounded-full px-4 py-2 text-sm"
                style={{ color: 'var(--text-secondary)' }}
              >
                {result.audio_result.verdict} · {(result.audio_result.fake_probability * 100).toFixed(1)}%
              </span>
            </div>
            <WaveformPlayer
              waveform={result.audio_result.waveform || asset?.waveform || []}
              url={asset?.previewUrl || ''}
              verdict={result.audio_result.verdict}
            />
          </section>
        ) : null}

      </div>
    </div>
  );
}

export default Results;
