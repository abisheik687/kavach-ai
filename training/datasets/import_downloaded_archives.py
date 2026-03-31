from __future__ import annotations

import argparse
import shutil
from collections import defaultdict
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[2]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def copy_unique(source: Path, destination_dir: Path) -> Path:
    ensure_dir(destination_dir)
    destination = destination_dir / source.name
    counter = 1
    while destination.exists():
        destination = destination_dir / f'{source.stem}_{counter}{source.suffix}'
        counter += 1
    shutil.copy2(source, destination)
    return destination


def gather_celeb_df_videos(staging_root: Path) -> dict[str, list[Path]]:
    mapping = {
        'real': [],
        'fake': [],
    }
    real_roots = [staging_root / 'Celeb-real', staging_root / 'YouTube-real']
    fake_roots = [staging_root / 'Celeb-synthesis']

    for root in real_roots:
        if root.exists():
            mapping['real'].extend(sorted(root.glob('*.mp4')))
    for root in fake_roots:
        if root.exists():
            mapping['fake'].extend(sorted(root.glob('*.mp4')))
    return mapping


def extract_frames_from_videos(
    videos: list[Path],
    destination_dir: Path,
    target_frames: int,
    frame_step_seconds: float,
    max_frames_per_video: int,
) -> int:
    ensure_dir(destination_dir)
    written = 0

    for video in videos:
        if written >= target_frames:
            break
        capture = cv2.VideoCapture(str(video))
        if not capture.isOpened():
            capture.release()
            continue

        fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
        stride = max(int(fps * frame_step_seconds), 1)
        total_frames_for_video = 0
        frame_index = 0
        try:
            while written < target_frames and total_frames_for_video < max_frames_per_video:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % stride == 0:
                    filename = destination_dir / f'{video.stem}_f{frame_index:06d}.jpg'
                    if not filename.exists():
                        cv2.imwrite(str(filename), frame)
                        written += 1
                        total_frames_for_video += 1
                frame_index += 1
        finally:
            capture.release()
    return written


def import_celeb_df(
    staging_root: Path,
    image_target_per_class: int,
    video_target_per_class: int,
    frame_step_seconds: float,
    max_frames_per_video: int,
) -> dict[str, int]:
    videos = gather_celeb_df_videos(staging_root)
    image_root = ROOT / 'data' / 'image' / 'celeb_df'
    video_root = ROOT / 'data' / 'video' / 'celeb_df'
    summary: dict[str, int] = {}

    for label in ('real', 'fake'):
        selected_videos = videos[label][:video_target_per_class]
        copied_videos = 0
        for video_path in selected_videos:
            copy_unique(video_path, video_root / label)
            copied_videos += 1
        summary[f'video_{label}'] = copied_videos

        frame_videos = videos[label]
        extracted_frames = extract_frames_from_videos(
            frame_videos,
            image_root / label,
            target_frames=image_target_per_class,
            frame_step_seconds=frame_step_seconds,
            max_frames_per_video=max_frames_per_video,
        )
        summary[f'image_{label}'] = extracted_frames

    return summary


def parse_asvspoof_protocols(protocol_dir: Path) -> dict[str, list[str]]:
    labels: dict[str, list[str]] = defaultdict(list)
    for protocol_path in sorted(protocol_dir.glob('*.txt')):
        with protocol_path.open('r', encoding='utf-8') as handle:
            for line in handle:
                parts = line.strip().split()
                if len(parts) < 2:
                    continue
                file_id = parts[1]
                label = parts[-1].lower()
                if label not in {'bonafide', 'spoof'}:
                    continue
                labels[label].append(file_id)
    return labels


def index_audio_files(audio_roots: list[Path]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for root in audio_roots:
        if not root.exists():
            continue
        for file_path in root.glob('*.flac'):
            index[file_path.stem] = file_path
    return index


def import_asvspoof(
    staging_root: Path,
    target_per_class: int,
) -> dict[str, int]:
    protocol_dir = staging_root / 'ASVspoof2019_LA_cm_protocols'
    audio_roots = [
        staging_root / 'ASVspoof2019_LA_train' / 'flac',
        staging_root / 'ASVspoof2019_LA_dev' / 'flac',
        staging_root / 'ASVspoof2019_LA_eval' / 'flac',
    ]
    audio_index = index_audio_files(audio_roots)
    labels = parse_asvspoof_protocols(protocol_dir)
    output_root = ROOT / 'data' / 'audio' / 'asvspoof'

    copied_counts = {'real': 0, 'fake': 0}
    label_map = {'bonafide': 'real', 'spoof': 'fake'}

    for source_label, destination_label in label_map.items():
        seen: set[str] = set()
        for file_id in labels.get(source_label, []):
            if copied_counts[destination_label] >= target_per_class:
                break
            if file_id in seen:
                continue
            source = audio_index.get(file_id)
            if source is None:
                continue
            copy_unique(source, output_root / destination_label)
            copied_counts[destination_label] += 1
            seen.add(file_id)
    return copied_counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Import downloaded Celeb-DF and ASVspoof archives into project data folders')
    parser.add_argument(
        '--celeb-staging',
        default=r'E:\Users\Abisheik\downloads\datasets\celeb_df_extracted',
        help='Extracted Celeb-DF root',
    )
    parser.add_argument(
        '--asvspoof-staging',
        default=r'E:\Users\Abisheik\downloads\datasets\asvspoof_la_extracted\LA',
        help='Extracted ASVspoof LA root',
    )
    parser.add_argument('--image-target-per-class', type=int, default=800)
    parser.add_argument('--video-target-per-class', type=int, default=150)
    parser.add_argument('--audio-target-per-class', type=int, default=1000)
    parser.add_argument('--frame-step-seconds', type=float, default=1.0)
    parser.add_argument('--max-frames-per-video', type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    celeb_summary = import_celeb_df(
        staging_root=Path(args.celeb_staging),
        image_target_per_class=args.image_target_per_class,
        video_target_per_class=args.video_target_per_class,
        frame_step_seconds=args.frame_step_seconds,
        max_frames_per_video=args.max_frames_per_video,
    )
    asvspoof_summary = import_asvspoof(
        staging_root=Path(args.asvspoof_staging),
        target_per_class=args.audio_target_per_class,
    )

    print('Celeb-DF import summary:')
    for key, value in celeb_summary.items():
        print(f'  {key}: {value}')
    print('ASVspoof import summary:')
    for key, value in asvspoof_summary.items():
        print(f'  {key}: {value}')


if __name__ == '__main__':
    main()
