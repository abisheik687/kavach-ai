const VERDICTS = {
    DEEPFAKE: { label: 'DEEPFAKE', bg: '#E63946', text: '#fff' },
    AUTHENTIC: { label: 'AUTHENTIC', bg: '#2DC653', text: '#fff' },
    UNCERTAIN: { label: 'UNCERTAIN', bg: '#F4A261', text: '#0A1628' },
    PROCESSING: { label: 'PROCESSING', bg: '#00B4D8', text: '#0A1628' },
};

export function VerdictBadge({ verdict, size = 'md', pulse = false }) {
    const v = VERDICTS[verdict?.toUpperCase()] ?? VERDICTS.UNCERTAIN;
    const sizes = {
        sm: 'px-2 py-0.5 text-xs', md: 'px-3 py-1 text-sm',
        lg: 'px-5 py-2 text-base', xl: 'px-8 py-3 text-xl'
    };
    return (
        <span
            className={`inline-flex items-center font-bold tracking-widest rounded
                  ${sizes[size]} ${pulse ? 'animate-pulse' : ''}`}
            style={{ backgroundColor: v.bg, color: v.text }}
        >
            {v.label}
        </span>
    );
}
