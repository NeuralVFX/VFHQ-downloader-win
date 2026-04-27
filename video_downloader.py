import os
import subprocess
import logging
from config import VIDEO_EXTENSIONS
import sys

from yt_dlp import YoutubeDL



class VideoDownloader:

        
    @staticmethod
    def check_video(output_dir, clip_meta):
        ################
        #  1. Check for the "Private" Marker File First
        ################
        private_marker = os.path.join(output_dir, f"vid_{clip_meta.video_id}.private")
        if os.path.exists(private_marker):
            logging.info(f"Skipping {clip_meta.video_id}: Marked as private/unavailable.")
            time.sleep(0.1) # Small breather for rapid-skipping
            return True # Returning True skips the download phase

        ################
        #  2. Normal Output Detection
        ################
        final_output_file_crop = os.path.join(
            output_dir, f"{clip_meta.video_id}_{clip_meta.pid}_crop.mp4")
        
        final_output_file_trim = os.path.join(
            output_dir, f"{clip_meta.video_id}_{clip_meta.pid}_trim.mp4")
            
        exists = False
        if os.path.exists(final_output_file_crop) and os.path.exists(final_output_file_trim):
            exists = True
            logging.info(
                f"Output Files {final_output_file_crop} {final_output_file_trim} already exist. Skipping processing.")
            time.sleep(0.1) # Breather
            
        return exists


            ###############
    
    @staticmethod
    def download_video_max(output_dir, meta_info, progress_bar, max_size_mb=1000, verbose=False):
        video_path_base = os.path.join(output_dir, f"vid_{meta_info.video_id}")
        
        command = [
            "yt-dlp",
            f"https://www.youtube.com/watch?v={meta_info.video_id}",
            "-o", f"{video_path_base}.%(ext)s",
            #"-f", "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "-f", "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "--merge-output-format", "mp4",
            "--cookies-from-browser", "firefox", # Specify firefox here
            #"--extractor-args", "youtube:player-client=web;getpot=true", # This is the critical key
            #"--extractor-args", "youtube:player-client=web",
            "--sleep-requests", "1.5", # Slows down the metadata handshake
            "--sleep-interval", "5",     
            "--max-sleep-interval", "30",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github", 
            "--no-part",
            "--buffer-size", "16M",
            "--retries", "3",
            "--fragment-retries", "3",
            "--skip-unavailable-fragments",
            #"--verbose",
            #"--progress",
            "--newline"
        ]
        if verbose:
            command += ["--verbose","--progress"]
                
        try:
            # bufsize=1 and universal_newlines=True prevents the pipe from "deadlocking"
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
                    print(line.strip())  # 👈 see EVERYTHING

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

    
    @staticmethod
    def download_video(output_dir, meta_info, progress_bar):
        progress_bar.set_description(f"Downloading")
        for ext in VIDEO_EXTENSIONS:
            existing_video_path = os.path.join(
                output_dir, f"vid_{meta_info.video_id}{ext}")
            if os.path.isfile(existing_video_path):
                logging.info(f'Video for ID {meta_info.video_id} already downloaded at {
                             existing_video_path}')
                return existing_video_path


        video_path = os.path.join(output_dir, f"vid_{meta_info.video_id}")
        command = [
            "yt-dlp",
            f"https://www.youtube.com/watch?v={meta_info.video_id}",
            "--output", f"{video_path}.%(ext)s",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--external-downloader", "aria2c",
            "--max-filesize", "250M",  ## ADDING THIS TO SKIP LARGE FILES
            "--external-downloader-args", "-x 16 -s 16 -k 1M --console-log-level=warn --quiet=true",
            "--quiet",
            "--concurrent-fragments", "16",
            "--buffer-size", "32K",
            "--http-chunk-size", "10M",
            "--fragment-retries", "infinite"
        ]

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        output_lines = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output.startswith("[download]"):
                output_lines.append(output.strip())
                sys.stdout.write("\033[F" * (len(output_lines) + 1))
                sys.stdout.write("\033[J")
                for line in output_lines:
                    print(line)
                progress_bar.display()

        return_code = process.poll()
        if return_code == 0:
            for ext in VIDEO_EXTENSIONS:
                downloaded_file = video_path + ext
                if os.path.isfile(downloaded_file):
                    logging.info(f'Successfully downloaded video for ID {
                                 meta_info.video_id} to {downloaded_file}')
                    return downloaded_file
        else:
            logging.error(f'Failed to download video for ID {
                          meta_info.video_id}: Process ended with return code {return_code}')

        return None



    @staticmethod
    def download_video_a(output_dir, meta_info, progress_bar):
        # 1. Check if the video already exists (Keep your existing logic)
        for ext in VIDEO_EXTENSIONS:
            existing_video_path = os.path.join(output_dir, f"vid_{meta_info.video_id}{ext}")
            if os.path.isfile(existing_video_path):
                logging.info(f'Video for ID {meta_info.video_id} already downloaded at {existing_video_path}')
                return existing_video_path

        # 2. Define the output path template
        # formatting it as vid_{id}.{ext} to match your requirements
        out_path_template = os.path.join(output_dir, f"vid_{meta_info.video_id}.%(ext)s")
        
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
