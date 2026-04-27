import os
from moviepy import VideoFileClip
import logging
from clip_meta import ClipMeta
import time

class VideoProcessor:
    @staticmethod
    def crop_video(clip_meta: ClipMeta, video_file, output_path):
        final_output_file_crop = os.path.join(output_path, f"{clip_meta.stem}_crop.mp4")
        final_output_file_trim = os.path.join(output_path, f"{clip_meta.stem}_trim.mp4")

        if not video_file:
            logging.info(f"No video file provided for {clip_meta.stem}.")
            return

        clip = VideoFileClip(video_file)
        trimmed_clip = clip.subclipped(clip_meta.start_t, clip_meta.end_t)

        # Write to temp names first, then rename atomically
        tmp_trim = final_output_file_trim + ".tmp.mp4"
        tmp_crop = final_output_file_crop + ".tmp.mp4"

        trimmed_clip.write_videofile(tmp_trim, codec="libx264", preset="ultrafast", audio_codec="aac", threads=4, logger=None)
        cropped_clip = trimmed_clip.cropped(x1=clip_meta.x0, y1=clip_meta.y0, x2=clip_meta.x1, y2=clip_meta.y1)
        cropped_clip.write_videofile(tmp_crop, codec="libx264", preset="ultrafast", audio_codec="aac", threads=4, logger=None)
        clip.close()

        os.rename(tmp_trim, final_output_file_trim)
        os.rename(tmp_crop, final_output_file_crop)
        logging.info(f"Video processed and saved as {final_output_file_crop}")
        logging.info(f"Video processed and saved as {final_output_file_crop}")
