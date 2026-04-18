import subprocess
import re
import logging
from typing import Callable
from utilities import time_to_seconds

logger = logging.getLogger("DownloaderApp")

class DownloadEngine:
    def __init__(self,
                 on_progress: Callable[[float, int], None],
                 on_success: Callable[[], None],
                 on_error: Callable[[str], None]):
        
        self.on_progress = on_progress
        self.on_success = on_success
        self.on_error = on_error

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
                    if not self.is_stopped_by_user:
                        self.on_error("СКАЧИВАНИЕ ПРЕРВАНО ИЗ-ЗА ОШИБКИ")
        except FileNotFoundError:
            self.on_error("ФАЙЛ ЗАПУСКА FFMPEG НЕ НАЙДЕН")
        except Exception as e:
            self.on_error(f'Ошибка FFMPEG: {e}')