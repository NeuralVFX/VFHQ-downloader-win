import os
import logging
import concurrent.futures
import threading
import time
from collections import defaultdict
from tqdm import tqdm

from video_downloader import VideoDownloader
from video_processor import VideoProcessor
from meta_parser import MetaParser
from config import META_DIR, VIDEO_DIR, OUTPUT_DIR


stats = {'total': 0, 'success': 0, 'failed': 0}
stats_lock = threading.Lock()


logging.basicConfig(filename='video_processing.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def ensure_directories_exist():
    dirs = [META_DIR, VIDEO_DIR, OUTPUT_DIR]
    for dir in dirs:
        os.makedirs(dir, exist_ok=True)

        
def process_single_video(video_id, clip_meta_list, video_dir, output_dir, progress_bar, verbose=False):
    global stats, stats_lock

    try:
        if VideoDownloader.check_video(output_dir, clip_meta_list):
            with stats_lock:
                stats['total'] += 1
                stats['success'] += 1
            return

        video_file = VideoDownloader.download_video_max(output_dir,
                                                        clip_meta_list[0],
                                                        progress_bar,
                                                        verbose=verbose)

        with stats_lock:
            stats['total'] += 1

        if not video_file:
            with stats_lock:
                stats['failed'] += 1
            time.sleep(15)
            return

        for clip_meta in clip_meta_list:
            VideoProcessor.crop_video(clip_meta, video_file, output_dir)

        if os.path.exists(video_file):
            os.remove(video_file)
            logging.info(f"Deleted base video: {video_file}")

        with stats_lock:
            stats['success'] += 1

    except Exception as e:
        with stats_lock:
            stats['failed'] += 1
        logging.error(f"Failed to process video {video_id}: {e}")
        time.sleep(20)

    finally:
        progress_bar.update(1)
        time.sleep(5)


def build_video_groups(meta_dir):
    """Parse all meta files and group by video_id, sorted deterministically."""
    meta_files = sorted(f for f in os.listdir(meta_dir) if f.endswith('.txt'))
    
    groups = defaultdict(list)
    for meta_file in meta_files:
        clip_meta = MetaParser.parse_clip_meta(os.path.join(meta_dir, meta_file))
        groups[clip_meta.video_id].append(clip_meta)

    # Sort clips within each video by (pid, clip_idx)
    for video_id in groups:
        groups[video_id].sort(key=lambda c: (c.pid, c.clip_idx))

    # Sort the dict by video_id alphabetically
    groups = dict(sorted(groups.items()))

    multi_clip = sum(1 for v in groups.values() if len(v) > 1)
    total_clips = sum(len(v) for v in groups.values())
    print(f"Videos:              {len(groups)}")
    print(f"Total clips:         {total_clips}")
    print(f"Multi-clip videos:   {multi_clip}")

    return groups


def run_pipeline(meta_dir, video_dir, output_dir, threaded=True, max_workers=3, verbose=False):
    global stats, stats_lock
    stats = {'total': 0, 'success': 0, 'failed': 0}
    stats_lock = threading.Lock()

    ensure_directories_exist()
    groups = build_video_groups(meta_dir)
    items = list(groups.items())

    start_time = time.time()
    with tqdm(total=len(items), unit='video') as progress_bar:
        if threaded:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures = [ex.submit(process_single_video, vid, clips, video_dir, output_dir, progress_bar)
                           for vid, clips in items]
                concurrent.futures.wait(futures)
        else:
            for vid, clips in items:
                process_single_video(vid, clips, video_dir, output_dir, progress_bar, verbose=verbose)

    elapsed = time.time() - start_time
    print(f"\nTime:    {elapsed:.2f}s")
    print(f"Total:   {stats['total']}")
    print(f"Success: {stats['success']}")
    print(f"Failed:  {stats['failed']}")
    

if __name__ == "__main__":
    run_pipeline(META_DIR, VIDEO_DIR, OUTPUT_DIR, threaded=True, max_workers=3)