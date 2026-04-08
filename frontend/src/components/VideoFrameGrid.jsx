import { motion } from 'framer-motion';

/**
 * @param {{ frames: { index: number, fake_probability: number, image_base64: string }[] }} props
 */
function VideoFrameGrid({ frames }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {frames.map((frame, index) => {
        const prob = frame.fake_probability;
        const scoreColor = prob >= 0.8 ? '#f87171' : prob >= 0.55 ? '#f5c842' : '#34d399';

        return (
          <motion.div
            key={`${frame.index}-${index}`}
            initial={{ opacity: 0, filter: 'blur(10px)', scale: 0.97 }}
            animate={{ opacity: 1, filter: 'blur(0px)', scale: 1 }}
            transition={{ delay: index * 0.07, duration: 0.4 }}
            className="panel overflow-hidden rounded-2xl"
          >
            <div className="relative">
              <img
                src={frame.image_base64}
                alt={`Analysed frame ${frame.index}`}
                className="aspect-video w-full object-cover"
              />
              <div
                className="absolute inset-x-0 bottom-0 px-4 py-3"
                style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.75), transparent)' }}
              >
                <div className="flex items-end justify-between gap-2">
                  <span
                    className="media-badge label-font rounded-full px-3 py-1 text-[11px] uppercase tracking-wider"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Frame {frame.index}
                  </span>
                  <span
                    className="heading-font text-lg"
                    style={{ color: scoreColor }}
                  >
                    {(prob * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

export default VideoFrameGrid;
