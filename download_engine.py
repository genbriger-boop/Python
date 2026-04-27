import subprocess
import time
import re
import logging
from typing import Callable
from utilities import time_to_seconds

logger = logging.getLogger("DownloaderApp")

class DownloadEngine:
    def __init__(self,
                 on_progress: Callable[[float, int], None],
                 on_success: Callable[[], None],
                 on_error: Callable[[str], None],
                 on_cancel: Callable[[], None]):
        
        self.on_progress = on_progress
        self.on_success = on_success
        self.on_error = on_error
        self.on_cancel = on_cancel

        self.process = None
        self.is_stopped_by_user = False
        self.current_tool = None

    def stop(self) -> None:
        self.is_stopped_by_user = True
        if self.process:
           try:
               if self.current_tool == "YT-DLP":
                   subprocess.Popen(f'cmd /c taskkill /f /pid {self.process.pid} /t')
               else:
                   self.process.terminate()
           except Exception as e:
               logger.error(f'Ошибка при остановке процесса: {e}')

    def download_via_ffmpeg(self, ffmpeg_path: str, url: str, output_file: str) -> None:
        self.current_tool = "FFMPEG"
        command = [ffmpeg_path, "-i", url, '-c', 'copy', output_file]
        try:
            with subprocess.Popen(command, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace') as self.process:
                total_duration = 0.0
                for line in self.process.stderr:
                    match_duration = re.search(r"Duration: (\d{2}:\d{2}:\d{2}\.\d{2})", line)
                    match_time = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})", line)
                    if match_duration:
                        clean_time = match_duration.group(1)
                        total_duration = time_to_seconds(clean_time)
                    elif match_time and total_duration > 0:
                        clean_time = match_time.group(1)
                        current_time = time_to_seconds(clean_time)
                        progress = current_time / total_duration
                        percent = int(progress * 100)
                        self.on_progress(progress, percent)
                self.process.wait()
                if self.process.returncode == 0:
                    self.on_success()
                else:
                    if self.is_stopped_by_user:
                        self.on_cancel(0, "0%", "Отменено", "red")
                    else:
                        self.on_error("СКАЧИВАНИЕ ПРЕРВАНО ИЗ-ЗА ОШИБКИ")
        except FileNotFoundError:
            self.on_error("ФАЙЛ ЗАПУСКА FFMPEG НЕ НАЙДЕН")
        except Exception as e:
            self.on_error(f'Ошибка FFMPEG: {e}')
    
    def download_via_yt_dlp(self, yt_dlp_path: str, entry: str, format_string: str, output_file: str, ffmpeg_path: str) -> None:
        self.current_tool = "YT-DLP"
        self.last_label_update = 0
        command = [yt_dlp_path, entry, '-f', format_string, '-o', output_file, '--newline', '--no-playlist', '--merge-output-format', 'mp4', "--ffmpeg-location", ffmpeg_path]
        try:
            with subprocess.Popen(command, stdout=subprocess.PIPE, encoding='utf-8', errors="replace") as self.process:
                for line in self.process.stdout:
                    match_search = re.search(r'\[download\]\s+(\d+(?:\.\d+)?)', line)
                    speed = re.search(r"at\s+([~0-9.]+[a-zA-Z]+/s)", line)
                    times = re.search(r"ETA\s+([\d:]+)", line)
                    if match_search:
                        raw_value = match_search.group(1)
                        value = float(raw_value)
                        progress_bar_value = value / 100
                        self.on_progress(progress_float = progress_bar_value, percent_int = int(value))
                    if speed and times:
                        current_time = time.time()
                        if current_time - self.last_label_update > 2:
                            s_val = speed.group(1)
                            t_val = times.group(1)
                            raw_text = f'Скорость: {s_val} | Осталось: {t_val}'
                            self.on_progress(sec_time_val = raw_text)
                            self.last_label_update = current_time
                self.process.wait()
                if self.process.returncode == 0:
                    self.on_success()
                else:
                    if self.is_stopped_by_user:
                        self.on_cancel(0, "0%", "Отменено", "red")
                    else:
                        self.on_error("СКАЧИВАНИЕ ПРЕРВАНО ИЗ-ЗА ОШИБКИ")
                    
        except FileNotFoundError:
            self.on_error("ПУТЬ К YT-DLP НЕ НАЙДЕН")
        except Exception as e:
            self.on_error(f'Ошибка YT-DLP: {e}')