import os
from moviepy import VideoFileClip
import logging
from clip_meta import ClipMeta


class VideoProcessor:
    @staticmethod
    def crop_video(clip_meta: ClipMeta, video_file, output_path):
        safe_video_id = 'anjie' + \
            clip_meta.video_id[1:] if clip_meta.video_id.startswith(
                "-") else clip_meta.video_id

        final_output_file_crop = os.path.join(
            output_path, f"{clip_meta.video_id}_{clip_meta.pid}_crop.mp4")
        
        final_output_file_trim = os.path.join(
            output_path, f"{clip_meta.video_id}_{clip_meta.pid}_trim.mp4")
        
        if os.path.exists(final_output_file_crop) and os.path.exists(final_output_file_trim):
            logging.info(
                f"File {final_output_file_crop} already exists. Skipping processing.")
            return

        if not video_file:
            logging.info(f"No video file provided for {
                         clip_meta.video_id}_{clip_meta.pid}.")
            return

        clip = VideoFileClip(video_file)
        
        trimmed_clip = clip.subclipped(clip_meta.start_t, clip_meta.end_t)

        trimmed_output_file = os.path.join(
            output_path, f"{safe_video_id}_{clip_meta.pid}_trim.mp4")
        trimmed_clip.write_videofile(
            trimmed_output_file, codec="libx264", preset="ultrafast", audio_codec="aac", threads=4, logger=None)

        
        cropped_clip = trimmed_clip.cropped(
            x1=clip_meta.x0, y1=clip_meta.y0, x2=clip_meta.x1, y2=clip_meta.y1)

        cropped_output_file = os.path.join(
            output_path, f"{safe_video_id}_{clip_meta.pid}_crop.mp4")
        cropped_clip.write_videofile(
            cropped_output_file, codec="libx264", preset="ultrafast", audio_codec="aac", threads=4, logger=None)
        clip.close()

        os.rename(trimmed_output_file, final_output_file_trim)
        os.rename(cropped_output_file, final_output_file_crop)
        ### added to clean up downloaded video
        os.remove(video_file)
        logging.info(f"Video processed and saved as {final_output_file_crop}")
