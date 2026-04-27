import os
import subprocess
import logging
from config import VIDEO_EXTENSIONS
import sys
import time
from yt_dlp import YoutubeDL



class VideoDownloader:

    @staticmethod
    def check_video(output_dir, clip_meta_list):
        # 1. Private marker check
        private_marker = os.path.join(output_dir, f"vid_{clip_meta_list[0].video_id}.private")
        if os.path.exists(private_marker):
            logging.info(f"Skipping {clip_meta_list[0].video_id}: Marked as private/unavailable.")
            time.sleep(0.1)
            return True
    
        # 2. Check ALL clips — if ANY are missing, return False (reprocess all)
        for clip_meta in clip_meta_list:
            crop = os.path.join(output_dir, f"{clip_meta.stem}_crop.mp4")
            trim = os.path.join(output_dir, f"{clip_meta.stem}_trim.mp4")
            if not (os.path.exists(crop) and os.path.exists(trim)):
                logging.info(f"Missing output for {clip_meta.stem}, will reprocess all clips.")
                time.sleep(0.1)
                return False
    
        logging.info(f"All clips for {clip_meta_list[0].video_id} already exist. Skipping.")
        time.sleep(0.1)
        return True

    @staticmethod
    def download_video_max(output_dir, meta_info, progress_bar, verbose=False):
        video_path_base = os.path.join(output_dir, f"vid_{meta_info.video_id}")
        
        command = [
            "yt-dlp",
            f"https://www.youtube.com/watch?v={meta_info.video_id}",
            "-o", f"{video_path_base}.%(ext)s",
            "-f", "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "--merge-output-format", "mp4",
            "--cookies-from-browser", "firefox",

            "--sleep-requests", "1.5", 
            "--sleep-interval", "5",     
            "--max-sleep-interval", "30",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github", 
            "--no-part",
            "--buffer-size", "16M",
            "--retries", "3",
            "--fragment-retries", "3",
            "--skip-unavailable-fragments",
            "--newline"
        ]
        if verbose:
            command += ["--verbose","--progress"]
                
        try:
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                universal_newlines=True,
                bufsize=1 
            )
            
            is_permanently_dead = False

            for line in process.stdout:
                if verbose:
                    print(line.strip())  

                # 1. Update the TQDM progress bar
                if "[download]" in line and "%" in line:
                    progress_bar.set_description(f"Downloading {meta_info.video_id}")
                
                # 2. Check for permanent failures
                # We specifically IGNORE "rate-limited" so we don't permanently flag good videos during an IP ban
                if ("Video unavailable" in line or "is private" in line) and "rate-limited" not in line:
                    is_permanently_dead = True
            
            process.wait()
            
            # --- EVALUATE THE RUN ---
            if process.returncode == 0:
                final_file = f"{video_path_base}.mp4"
                if os.path.isfile(final_file):
                    return final_file
                return None
            else:
                # If yt-dlp failed AND we detected a permanent block (deleted/private)
                if is_permanently_dead:
                    # Write the negative cache marker directly to the output_dir
                    marker_file = os.path.join(output_dir, f"vid_{meta_info.video_id}.private")
                    with open(marker_file, 'w') as f:
                        f.write("Dead link or Private")
                    logging.warning(f"Marked {meta_info.video_id} as permanently private/unavailable in output_dir.")
                
                return None
    
        except Exception as e:
            logging.error(f"Critical error in download_video_max for {meta_info.video_id}: {e}")
            return None
    

        # 3. Define a progress hook to update your progress_bar
        def progress_hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '').strip()
                progress_bar.set_description(f"Downloading {percent}")
                # If your progress_bar supports integer updates (like tqdm), you could add that logic here

        # 4. Configure yt_dlp options
        ydl_opts = {
            'format': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
            'merge_output_format': 'mp4',  # Ensures the final file is always mp4
            'outtmpl': out_path_template,
            'quiet': True,                 # Reduces console noise
            'no_warnings': True,
            'progress_hooks': [progress_hook],
        }

        # 5. Execute Download
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={meta_info.video_id}"])
            
            # 6. Return the final file path
            # Since we forced merge_output_format='mp4', we know the extension.
            final_path = os.path.join(output_dir, f"vid_{meta_info.video_id}.mp4")
            
            if os.path.isfile(final_path):
                logging.info(f"Successfully downloaded video for ID {meta_info.video_id} to {final_path}")
                return final_path
            else:
                # Fallback check in case it didn't merge or used a different ext
                logging.warning(f"Expected file {final_path} not found, checking other extensions...")
                for ext in VIDEO_EXTENSIONS:
                    path = os.path.join(output_dir, f"vid_{meta_info.video_id}{ext}")
                    if os.path.isfile(path):
                        return path
                
        except Exception as e:
            logging.error(f"Failed to download video for ID {meta_info.video_id}: {str(e)}")
            return None
