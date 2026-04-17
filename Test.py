import tkinter as tk
import customtkinter as ctk
import subprocess
import threading
from tkinter import messagebox
import json
import os
from tkinter import filedialog
import re
import time
import queue
from datetime import datetime
import logging
from typing import TypedDict

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("app_log.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DownloaderApp")

class AppSetting(TypedDict):
    ffmpeg_path: str
    save_folder_path: str
    yt_dlp_path: str
    download_method: str
    selected_qual: str
    rows_count: int

class VideoTask: # Класс должен управлять только тем что сам создал! self нужно использовать только в классе! За пределами класса использую другие названия аргументов
    def __init__(self, master: ctk.CTkFrame, on_status_change, del_row, setting: AppSetting, get_mode, save_selected_qual, calculation_rows, total_downloaded_bytes, add_history):
        self.master_frame = master
        self.on_status_change = on_status_change
        self.del_row = del_row
        self.setting = setting
        self.get_mode = get_mode
        self.save_selected_qual = save_selected_qual
        self.calc_the_row = calculation_rows
        self.update_total_bytes = total_downloaded_bytes
        self.add_to_history = add_history
        self.process = None # Класс знает о переменной только в момент чтения этой переменной. Поэтому эту переменную нельзя создать просто в функции download_task

        self.row_frame = ctk.CTkFrame(master, fg_color="transparent", border_width=2, border_color="#436241")
        self.row_frame.pack(pady=5, ipady=8)
        self.link_entry = ctk.CTkEntry(self.row_frame, width=350, placeholder_text="Ссылка .m3u8...")
        self.link_entry.pack(side="left", pady=5, padx=5)
        self.link_entry.bind("<Key>", self.reset_is_successfully_downloaded)
        self.video_name = ctk.CTkEntry(self.row_frame, width=150, placeholder_text="Имя файла...")
        self.video_name.pack(side="left", padx=5,pady=5)
        self.video_name.bind("<Key>", self.reset_is_successfully_downloaded)
        self.choose_video_qual = ctk.CTkOptionMenu(self.row_frame, values=["HD4K", "HQ2K", "1080", "720", "480", "360"], width=75, dropdown_fg_color="#1F6AA5", command=self.save_selected_video_quality)
        self.choose_video_qual.pack(side='left', padx=5)
        self.choose_video_qual.set(self.setting.get('selected_qual', "1080"))
        if get_mode() == "FFMPEG":
            self.choose_video_qual.configure(state="disabled")
        self.progress_frame = ctk.CTkFrame(self.row_frame, fg_color="transparent", bg_color="transparent")
        self.progress_frame.pack(side="left", padx=5)
        self.progressbar = ctk.CTkProgressBar(self.progress_frame, fg_color="#3F3F3F", progress_color="green", width=125, height=15, mode="determinate", border_width=1, border_color="green")
        self.progressbar.set(0)
        self.progressbar.pack(side="top", padx=8, pady=5)
        self.speedRemaining_time = ctk.CTkLabel(self.progress_frame, text="Ожидание...", text_color="grey")
        self.speedRemaining_time.pack(side="bottom", padx=2)
        self.progress_percent = ctk.CTkLabel(self.row_frame, text="0%", text_color="green")
        self.progress_percent.pack(side="left", padx=7)
        self.download_btn = ctk.CTkButton(self.row_frame, text="Скачать", fg_color="green", width=1, command=self.preparing_to_download)
        self.download_btn.pack(side="left", padx=5, pady=5)
        self.stop_btn = ctk.CTkButton(self.row_frame, width=1, text="Стоп", fg_color="#76267a", state="disabled", command=self.stop_downloading)
        self.stop_btn.pack(side="left", padx=5)
        self.del_row_btn = ctk.CTkButton(self.row_frame, text="X", fg_color="red", width=1, command=self.del_the_row)
        self.del_row_btn.pack(side='left', padx=5, pady=5)
        self.last_label_update = 0
        self._is_downloading = False
        self.is_stopped_by_user = False
        self.is_successfully_downloaded = False

    def save_selected_video_quality(self, selected_value: str) -> None:
        self.save_selected_qual(selected_value)

    def reset_is_successfully_downloaded(self, event: tk.Event) -> None:
        if self.is_successfully_downloaded:
            self.is_successfully_downloaded = False

    def stop_downloading(self) ->None:
        self.is_stopped_by_user = True
        current_mode = self.get_mode()
        if current_mode == "FFMPEG":
            if self.process:
                self.process.terminate()
            else:
                self.speedRemaining_time.configure(text="Ожидание...", text_color="grey")
                self.master_frame.after(0, self.unlock_interface)
        elif current_mode == "YT-DLP":
            if self.process:
                subprocess.Popen(f'cmd /c taskkill /f /pid {self.process.pid} /t')
            else:
                self.speedRemaining_time.configure(text="Ожидание...", text_color="grey")
                self.master_frame.after(0, self.unlock_interface)
    
    def del_the_row(self) -> None:
        if self._is_downloading:
            return
        self.row_frame.destroy()
        if self.del_row:
            self.del_row(self)
        if self.calc_the_row:
            self.calc_the_row()

    def lock_interface(self) -> None:
        self._is_downloading = True
        self.is_stopped_by_user = False
        self.link_entry.configure(state="disabled")
        self.video_name.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self.del_row_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.speedRemaining_time.configure(text="В очереди...", text_color="grey")
        if self.on_status_change:
            self.on_status_change("disabled")

    def unlock_interface(self) -> None:
        self._is_downloading = False
        self.process = None
        self.link_entry.configure(state="normal")
        self.video_name.configure(state="normal")
        self.download_btn.configure(state="normal")
        self.del_row_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if self.on_status_change:
            self.on_status_change("normal")
 
    def preparing_to_download(self) -> None:
        if self._is_downloading:
            logger.warning("Попытка запустить скачивание когда скачивание уже идёт")
            messagebox.showerror("ОШИБКА", "ПРОЦЕСС ЗАНЯТ")
            return
        if not self.link_entry.get().strip() or not self.video_name.get().strip():
            logger.warning("Попытка загрузки видео с пустыми полями ссылки или названия видео")
            messagebox.showerror("ОШИБКА", "ЗАПОЛНИТЕ ОБА ПОЛЯ ДЛЯ ЗАГРУЗКИ ВИДЕО")
            return
        if not self.setting['save_folder_path']:
            logger.warning("Не указана папка для сохранения видео")
            messagebox.showerror("ОШИБКА", "НЕ УКАЗАНА ПАПКА ДЛЯ СОХРАНЕНИЯ ВИДЕО")
            return
        current_mode = self.get_mode()
        if current_mode == "FFMPEG":
            if not self.setting['ffmpeg_path']:
                messagebox.showerror("ОШИБКА", "НЕ УКАЗАН ПУТЬ К FFMPEG")
                return
        elif current_mode == "YT-DLP":
            if not self.setting['yt_dlp_path']:
                messagebox.showerror("ОШИБКА", "НЕ УКАЗАН ПУТЬ К YT-DLP")
                return
        self.lock_interface()
        threading.Thread(target=self.download_task, daemon=True).start()

    def download_task(self, open_folder: bool = True) -> None:
        self.entry = self.link_entry.get().strip()
        vname = self.video_name.get().strip()
        self.fix_vname = re.sub(r'[\\/:*?"<>|]', "_", vname)
        if self.is_stopped_by_user:
            logger.warning("Скачивание видео отменено до начала загрузки")
            return
        self.output_file = os.path.join(self.setting.get('save_folder_path', ""), f"{self.fix_vname}.mp4")
        current_mode = self.get_mode()
        logger.info(f'Начинается скачивание через {current_mode}. Файл {self.fix_vname}')
        if current_mode == 'FFMPEG':
            self.download_via_ffmpeg(open_folder)
        elif current_mode == 'YT-DLP':
            self.download_via_yt_dlp(open_folder)

    def download_via_ffmpeg(self, open_folder: bool) -> None:
        command = [self.setting.get('ffmpeg_path', ""), "-i", self.entry, '-c', 'copy', self.output_file]
        try:
            with subprocess.Popen(command, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace') as self.process:
                total_duration = 0.0
                for line in self.process.stderr:
                    match_duration = re.search(r"Duration: (\d{2}:\d{2}:\d{2}\.\d{2})", line)
                    match_time = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})", line)
                    if match_duration:
                        clean_time = match_duration.group(1)
                        total_duration = self.time_to_seconds(clean_time)
                    elif match_time and total_duration > 0:
                        clean_time = match_time.group(1)
                        current_time = self.time_to_seconds(clean_time)
                        progress = current_time / total_duration
                        percent = int(progress * 100)
                        self.master_frame.after(0, self.progressbar.set, progress)
                        self.master_frame.after(0, lambda p=percent: self.progress_percent.configure(text=f'{p}%'))
                self.process.wait()
                if self.process.returncode == 0:
                    self.is_successfully_downloaded = True
                    self.add_to_history(self.fix_vname, self.entry, "Успешно")
                    if os.path.exists(self.output_file):
                        file_size = os.path.getsize(self.output_file)
                        self.update_total_bytes(file_size)
                    self.master_frame.after(0, self.progress_bar_and_percent_reset, 1, "100%", "Готово", "green")
                    self.master_frame.after(0, self.progressbar.set, 1.0)
                    self.master_frame.after(0, lambda: self.progress_percent.configure(text="100%"))
                    if open_folder:
                        self.open_folder_after_downloading()
                else:
                    if self.is_stopped_by_user:
                        self.del_video_file()
                        self.master_frame.after(0, self.progress_bar_and_percent_reset, 0, "0%", "Остановлено", "red")
                    else:
                        logger.error(f"Скачивание прерванно из-за ошибки (код ошибки {self.process.returncode})")
                        self.master_frame.after(0, self.messages_error, "ОШИБКА", "СКАЧИВАНИЕ ПРЕРВАНО ИЗ-ЗА ОШИБКИ")
        except FileNotFoundError:
            self.master_frame.after(0, self.messages_error, "ОШИБКА", "ПУТЬ К FFMPEG НЕ НАЙДЕН")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в download_via_ffmpeg: {e}", exc_info=True)
            self.master_frame.after(0, self.messages_error, "ОШИБКА", f"{e}")
        finally:
            self.master_frame.after(0, self.unlock_interface)

    def download_via_yt_dlp(self, open_folder: bool) -> None:
        selected_quality = self.choose_video_qual.get()
        quality_formats = {
            'HD4K': 'bestvideo[height<=2160]+bestaudio/best',
            'HQ2K': 'bestvideo[height<=1440]+bestaudio/best',
            '1080': 'bestvideo[height<=1080]+bestaudio/best',
            '720': 'bestvideo[height<=720]+bestaudio/best',
            '480': 'bestvideo[height<=480]+bestaudio/best',
            '360': 'bestvideo[height<=360]+bestaudio/best'
        }
        format_string = quality_formats.get(selected_quality, 'best')
        command = [self.setting['yt_dlp_path'], self.entry, '-f', format_string, '-o', self.output_file, '--newline', '--no-playlist', '--merge-output-format', 'mp4', "--ffmpeg-location", self.setting['ffmpeg_path']]
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
                        self.master_frame.after(0, self.progressbar.set, progress_bar_value)
                        self.master_frame.after(0, lambda v=value: self.progress_percent.configure(text=f'{int(v)}%'))
                    if speed and times:
                        current_time = time.time()
                        if current_time - self.last_label_update > 2:
                            s_val = speed.group(1)
                            t_val = times.group(1)
                            raw_text = f'Скорость: {s_val} | Осталось: {t_val}'
                            self.master_frame.after(0, lambda r=raw_text: self.speedRemaining_time.configure(text=r))
                            self.last_label_update = current_time
                self.process.wait()
                if self.process.returncode == 0:
                    self.is_successfully_downloaded = True
                    self.add_to_history(self.fix_vname, self.entry, "Успешно")
                    if os.path.exists(self.output_file):
                        file_size = os.path.getsize(self.output_file)
                        self.update_total_bytes(file_size)
                    self.master_frame.after(0, self.progress_bar_and_percent_reset, 1, "100%", "Готово", "green")
                    if open_folder:
                        self.open_folder_after_downloading()
                else:
                    if self.is_stopped_by_user:
                        self.del_video_file()
                        self.master_frame.after(0, self.progress_bar_and_percent_reset, 0, "0%", "Остановлено", "red")
                    else:
                        logger.error(f"Скачивание прерванно из-за ошибки {self.process.returncode}")
                        self.master_frame.after(0, self.messages_error, "ОШИБКА", "СКАЧИВАНИЕ ПРЕРВАНО ИЗ-ЗА ОШИБКИ")
        except FileNotFoundError:
            self.master_frame.after(0, self.messages_error, "ОШИБКА", "ПУТЬ К YT-DLP НЕ НАЙДЕН")
        except Exception as e:
            logger.error(f"Скачивание преравно из-за ошибки {e}", exc_info=True)
            self.master_frame.after(0, self.messages_error, "ОШИБКА", f"{e}")
        finally:
            self.master_frame.after(0, self.unlock_interface)

    def del_video_file(self) -> None:
        folder = os.path.dirname(self.output_file)
        search_file = os.listdir(folder)
        for file in search_file:
            if file.startswith(self.fix_vname):
                file_path = os.path.join(folder, file)
                os.remove(file_path)

    def progress_bar_and_percent_reset(self, bar_value: float, percent_value:str, status_text: str, status_color:str) -> None:
        self.progressbar.set(bar_value)
        self.progress_percent.configure(text=percent_value)
        self.speedRemaining_time.configure(text=status_text, text_color=status_color)

    def open_folder_after_downloading(self) -> None:
        norm_path = os.path.normpath(self.output_file)
        if self.setting['save_folder_path'] and self.output_file:
            subprocess.Popen(f'explorer /select,{norm_path}')
        else:
            os.startfile(self.setting['save_folder_path'])

    def messages_error(self, title, text) -> None:
        messagebox.showerror(title, text)

    def time_to_seconds(self, time_str: str) -> float:
        h, m, s = time_str.split(':')
        total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
        return total_seconds

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("M3U8 Downloader")
        self.setting_file = "setting.json"
        self.history_file = "history.json"
        self.setting = self.load_setting()
        self.ffmpeg_path = self.setting.get('ffmpeg_path', "")
        self.save_folder_path = self.setting.get('save_folder_path', "")
        self.yt_dlp_path = self.setting.get('yt_dlp_path', "")
        self.download_method = self.setting.get('download_method', "FFMPEG")
        self.rows_count = self.setting.get('rows_count', 1)
        self.all_rows: list[VideoTask] = []
        self.stop_all_downloads = threading.Event()
        self.total_downloaded_bytes = 0
        self.counter_lock = threading.Lock()
        self.history_lock = threading.Lock()
        self.queue_box = queue.Queue()
        for _ in range(4):
            threading.Thread(target=self.download_all_task, daemon=True).start()
        self.geometric_calculation(1150, 650)
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing_app)

        if self.ffmpeg_path:
            self.choose_ffmpeg_btn.configure(border_color="green")
        if self.yt_dlp_path:
            self.choose_yt_dlp_btn.configure(border_color="green")

        for _ in range(self.rows_count):
            self.add_new_row()

        if self.download_method == "YT-DLP":        
            self.choose_download_option.set("YT-DLP")
            for row in self.all_rows:
                row.choose_video_qual.configure(state="normal")
        else:
            self.choose_download_option.set("FFMPEG")
            for row in self.all_rows:
                row.choose_video_qual.configure(state='disabled')

    def geometric_calculation(self, w: int, h: int) -> None:
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        scalling = self._get_window_scaling()
        x = int((ws-w) * scalling / 2)
        y = int((hs-h) * scalling / 2 - 150)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def choose_folder_path(self):
        user_path = filedialog.askdirectory(title="Укажите папку для сохранения видео")
        if user_path:
            self.save_folder_path = user_path
            self.folder_path_box.set(self.save_folder_path)
            self.setting['save_folder_path'] = self.save_folder_path
            self.save_setting()

    def choose_ffmpeg_path(self):
        user_path = filedialog.askopenfilename(title="Укажите путь к FFmpeg", filetypes=[("ffmpeg.exe", "ffmpeg.exe")])
        if user_path:
            self.ffmpeg_path = user_path
            self.choose_ffmpeg_btn.configure(border_color="green")
            self.setting['ffmpeg_path'] = self.ffmpeg_path
            self.save_setting()
                                           
    def choose_yt_dlp_path(self):
        user_path = filedialog.askopenfilename(title="Укажите путь к файлу запуска yt-dlp", filetypes=[('yt-dlp.exe', 'yt-dlp.exe')])
        if user_path:
            self.yt_dlp_path = user_path
            self.choose_yt_dlp_btn.configure(border_color="green")
            self.setting['yt_dlp_path'] = self.yt_dlp_path
            self.save_setting()

    def selected_download_method(self, event):
        self.setting['download_method'] = event
        self.save_setting()
        if event == "FFMPEG":
            for row in self.all_rows:
                row.choose_video_qual.configure(state="disabled")
        else:
            for row in self.all_rows:
                row.choose_video_qual.configure(state='normal')

    def change_global_buttn(self, button_state):
        if button_state == "normal":
            if any(row._is_downloading for row in self.all_rows):
                return
        self.download_sequence_btn.configure(state=button_state)
        self.download_all_btn.configure(state=button_state)
        self.delete_all_rows_btn.configure(state=button_state)
    
    def remove_from_all_rows(self, task):
        self.all_rows.remove(task)

    def delete_all_rows(self):
        for row in self.all_rows[:]:
            row.del_the_row()
        self.add_new_row()

    def open_folder_task(self):
        if not self.save_folder_path:
            messagebox.showerror("ОШИБКА", "ПАПКА НЕ ВЫБРАНА")
            return
        os.startfile(self.save_folder_path)

    def setup_ui(self):
        self.save_folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.save_folder_frame.pack(pady=5)
        self.path_label = ctk.CTkLabel(self.save_folder_frame, text="Сохранять в:")
        self.path_label.pack(side="left", padx=3)
        self.folder_path_box = ctk.StringVar(value=self.save_folder_path)
        self.path_entry = ctk.CTkEntry(self.save_folder_frame, width=300, textvariable=self.folder_path_box, state="disabled")
        self.path_entry.pack(side="left", padx=5)
        self.choose_folder_btn = ctk.CTkButton(self.save_folder_frame, text="Обзор", fg_color="blue", width=1, command=self.choose_folder_path)
        self.choose_folder_btn.pack(side="left")
        self.choose_ffmpeg_btn = ctk.CTkButton(self.save_folder_frame, text="FFMPEG", width=1, border_width=2, border_color="red", command=self.choose_ffmpeg_path)
        self.choose_ffmpeg_btn.pack(side="left", padx=10)
        self.choose_yt_dlp_btn = ctk.CTkButton(self.save_folder_frame, text="YT-DLP", width=1, border_width=2, border_color="red", command=self.choose_yt_dlp_path)
        self.choose_yt_dlp_btn.pack(side='left')
        self.choose_download_option = ctk.CTkOptionMenu(self.save_folder_frame, values=["FFMPEG", "YT-DLP"], width=90, dropdown_fg_color="#1F6AA5", command=self.selected_download_method)
        self.choose_download_option.pack(side="left", padx=10)

        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)

        self.buttn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttn_frame.pack(pady=(0,20))
        self.first_btn_frame = ctk.CTkFrame(self.buttn_frame, fg_color="transparent")
        self.first_btn_frame.pack()
        self.add_row_btn = ctk.CTkButton(self.first_btn_frame, text="ДОБАВИТЬ ВИДЕО", font=("Arial", 14, "bold"), width=150, command=self.add_new_row)
        self.add_row_btn.pack(side='left', pady=10, padx=20)
        self.load_txt_btn = ctk.CTkButton(self.first_btn_frame, text="ИМПОРТ ИЗ TXT", font=("Arial", 14, "bold"), width=150, command=self.load_from_txt)
        self.load_txt_btn.pack(side='left')
        self.four_btn_frame = ctk.CTkFrame(self.buttn_frame, fg_color="transparent")
        self.four_btn_frame.pack(pady=10)
        self.download_sequence_btn = ctk.CTkButton(self.four_btn_frame, text="ПО ОЧЕРЕДИ", font=("Arial", 14, "bold"), width=150, command=self.download_sequence)
        self.download_sequence_btn.pack(side="left", padx=10)
        self.download_all_btn = ctk.CTkButton(self.four_btn_frame, text="ОДНОВРЕМЕННО", font=("Arial", 14, "bold"), width=150, command=self.start_download_all)
        self.download_all_btn.pack(side="left", padx=10)
        self.delete_all_rows_btn = ctk.CTkButton(self.four_btn_frame, text="УДАЛИТЬ СТРОКИ", font=("Arial", 14, "bold"), width=150, command=self.delete_all_rows)
        self.delete_all_rows_btn.pack(side="left", padx=10)
        self.stop_all_downloads_btn = ctk.CTkButton(self.four_btn_frame, text="СТОП ВСЕ", font=("Arial", 14, "bold"), width=150, command=self.stop_all_downloads_task)
        self.stop_all_downloads_btn.pack(side="left", padx=10)
        self.open_save_folder_btn = ctk.CTkButton(self.buttn_frame, text="ОТКРЫТЬ ПАПКУ", font=("Arial", 14, "bold"), width=150, command=self.open_folder_task)
        self.open_save_folder_btn.pack(pady=10)
        self.total_downloaded_bytes_label = ctk.CTkLabel(self.buttn_frame, text="Всего загружено: 0 ГБ", text_color="grey")
        self.total_downloaded_bytes_label.pack(pady=5)
    
    def load_setting(self):
        if os.path.exists(self.setting_file):
            try:
                with open (self.setting_file, "r", encoding="utf-8") as file:
                    return json.load(file)
            except json.JSONDecodeError:
                return {'ffmpeg_path': "", 'save_folder_path': "", 'yt_dlp_path': "", 'download_method': "FFMPEG", 'selected_qual': "1080", 'rows_count': 1}
        return {'ffmpeg_path': "", 'save_folder_path': "", 'yt_dlp_path': "", 'download_method': "FFMPEG", 'selected_qual': "1080", 'rows_count': 1}

    def save_setting(self):
        with open (self.setting_file, "w", encoding="utf-8") as file:
            json.dump(self.setting, file, ensure_ascii=False, indent=4)
    
    def add_to_history(self, file_name, url, status):
        
        with self.history_lock:
            if os.path.exists(self.history_file):
                try:
                    with open(self.history_file, 'r', encoding='utf-8') as file:
                        history_data = json.load(file)
                except json.JSONDecodeError:
                    history_data = []
            else:
                history_data = []
            
            new_entry = {
                'name': file_name,
                'url': url,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                "status": status
            }

            history_data.insert(0, new_entry)

            history_data = history_data[:50]

            with open(self.history_file, 'w', encoding='utf-8') as file:
                json.dump(history_data, file, ensure_ascii=False, indent=4)

    def calc_rows(self):
        count_of_rows = len(self.all_rows)
        self.setting['rows_count'] = count_of_rows
        self.save_setting()

    def save_selected_qual_task(self, data):
        self.setting['selected_qual'] = data
        self.save_setting()

    def load_from_txt(self):
        file_path = filedialog.askopenfilename(title="Выберите файл с данными", filetypes=[('Text files', '*.txt')])

        if not file_path:
            return
        
        with open(file_path, 'r', encoding='utf-8') as file:
            data = file.readlines()
        
        links_list = []
        for d in data:
            parts = d.strip()
            if parts:
                links_list.append(parts)
        
        combine_data = list(zip(links_list[::2], links_list[1::2]))

        for link, name in combine_data:
            if not (link.startswith('http') and link.endswith('.m3u8')):
                messagebox.showerror("ОШИБКА", "НЕ ВСЕ ДАННЫЕ СООТВЕТСТВУЮТ СТАНДАРТУ.\nПРОВЕРЬТЕ ССЫЛКИ И НАЗВАНИЯ")
                return

        for row in self.all_rows[:]:
            row.del_the_row()

        for link, name in combine_data:
            self.add_new_row()
            last_row = self.all_rows[-1]
            last_row.link_entry.insert(0, link)
            last_row.video_name.insert(0, name)

    def add_new_row(self):
        new_row = VideoTask(self.main_frame, 
                            on_status_change=self.change_global_buttn, 
                            del_row=self.remove_from_all_rows, 
                            setting=self.setting, 
                            get_mode=self.choose_download_option.get, 
                            save_selected_qual=self.save_selected_qual_task, 
                            calculation_rows=self.calc_rows,
                            total_downloaded_bytes=self.update_bytes_progress,
                            add_history = self.add_to_history
                            )
        self.all_rows.append(new_row)
        self.calc_rows()

    def update_bytes_progress(self, new_bytes):
        with self.counter_lock:
            self.total_downloaded_bytes += new_bytes
            bytes_to_gb = self.total_downloaded_bytes / (1024**3)
            self.total_downloaded_bytes_label.configure(text=f'Всего загружено: {bytes_to_gb:.2f} ГБ')

    def stop_all_downloads_task(self):
        self.stop_all_downloads.set()

        while not self.queue_box.empty():
            try:
                self.queue_box.get_nowait()
                self.queue_box.task_done()
            except queue.Empty:
                break

        for row in self.all_rows:
            row.stop_downloading()

    def pre_download_check(self):
        for row in self.all_rows:
            if row._is_downloading:
                return False
            if not row.link_entry.get().strip() or not row.video_name.get().strip():
                messagebox.showerror("ОШИБКА", "ЗАПОЛНИТЕ ВСЕ ПОЛЯ ДЛЯ ЗАГРУЗКИ ВИДЕО ФАЙЛОВ")
                return False
            if not row.setting['save_folder_path']:
                messagebox.showerror("ОШИБКА", "НЕ УКАЗАНА ПАПКА ДЛЯ СОХРАНЕНИЯ ВИДЕО")
                return False
            current_mode = self.choose_download_option.get()
            if current_mode == "FFMPEG":
                if not row.setting['ffmpeg_path']:
                    messagebox.showerror("ОШИБКА", "НЕ УКАЗАН ПУТЬ К FFMPEG")
                    return False
            elif current_mode == "YT-DLP":
                if not row.setting['yt_dlp_path']:
                    messagebox.showerror("ОШИБКА", "НЕ УКАЗАН ПУТЬ К YT-DLP")
                    return False
        for row in self.all_rows:
            if not row.is_successfully_downloaded:
                row.lock_interface()
        return True

    def download_sequence(self):
        if not self.pre_download_check():
            return
        threading.Thread(target=self._download_sequence_thread).start()

    def _download_sequence_thread(self):
        for row in self.all_rows:
            if self.stop_all_downloads.is_set():
                return
            if not row.is_successfully_downloaded:
                row.download_task(open_folder=False)
        if any (row.is_successfully_downloaded for row in self.all_rows):
            self.open_folder_task()

    def start_download_all(self):
        threading.Thread(target=self.collect_the_tasks).start()

    def collect_the_tasks(self):
        if not self.pre_download_check():
            return
        self.stop_all_downloads.clear()
        task_added = False

        for row in self.all_rows:
            if not row.is_successfully_downloaded:
                self.queue_box.put(row)
                task_added = True

        if task_added:
            self.queue_box.join()
            if not self.stop_all_downloads.is_set():
                if any(row.is_successfully_downloaded for row in self.all_rows):
                    self.open_folder_task()

    def download_all_task(self):
        while True:
            row_obj = self.queue_box.get()

            if self.stop_all_downloads.is_set():
                self.queue_box.task_done()
                continue

            row_obj.download_task(open_folder=False)
            self.queue_box.task_done()

    def on_closing_app(self):
        
        self.stop_all_downloads_task()
        
        self.destroy()

# region СТАРЫЙ МНОГОПОТОЧНЫЙ РЕЖИМ
    def download_all(self):
        if not self.pre_download_check():
            return
        threading.Thread(target=self._download_all_thread).start()
    
    def _download_all_thread(self):
        all_threads = []
        bouncer = threading.Semaphore(5)

        def download_with_semaphore(row_obj):
            with bouncer:
                if self.stop_all_downloads.is_set():
                    return
                row_obj.download_task(open_folder=False)

        for row in self.all_rows:
            if not row.is_successfully_downloaded:
                t = threading.Thread(target=download_with_semaphore, args=(row,))
                t.start()
                all_threads.append(t)
        for t in all_threads:
            t.join()
        if any(row.is_successfully_downloaded for row in self.all_rows):
            self.open_folder_task()
#endregion

if __name__ == "__main__":
    app = App()
    app.mainloop()