import tkinter as tk
import customtkinter as ctk
import logging
import threading
from tkinter import messagebox
import os
from tkinter import filedialog
import subprocess
import re
from settings import AppSetting, load_setting, save_setting
from history_manager import add_to_history
from download_engine import DownloadEngine
from queue_manager import DownloadQueueManager
from load_from_txt import parse_txt_file

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


class VideoRowUI:
    def __init__(self, master: ctk.CTkFrame, default_qual: str):
        self.master_frame = master
        self.on_download_click = None
        self.on_delete_click = None
        self.on_stop_click = None
        self.reset_flag_is_successfully_downloaded = None
        self.save_video_qual = None

        self.row_frame = ctk.CTkFrame(master, fg_color="transparent", border_width=2, border_color="#436241")
        self.row_frame.pack(pady=5, ipady=8)
        self.link_entry = ctk.CTkEntry(self.row_frame, width=350, placeholder_text="Ссылка .m3u8...")
        self.link_entry.pack(side="left", pady=5, padx=5)
        self.link_entry.bind("<Key>", self.on_typing_key_in_row)
        self.save_border_color = self.link_entry.cget('border_color')
        self.video_name = ctk.CTkEntry(self.row_frame, width=150, placeholder_text="Имя файла...")
        self.video_name.pack(side="left", padx=5,pady=5)
        self.video_name.bind("<Key>", self.on_typing_key_in_row)
        self.choose_video_qual = ctk.CTkOptionMenu(self.row_frame, values=["HD4K", "HQ2K", "1080", "720", "480", "360"], width=75, dropdown_fg_color="#1F6AA5", command=self._on_choose_video_qual)
        self.choose_video_qual.pack(side='left', padx=5)
        self.choose_video_qual.set(default_qual)
        self.progress_frame = ctk.CTkFrame(self.row_frame, fg_color="transparent", bg_color="transparent")
        self.progress_frame.pack(side="left", padx=5)
        self.progressbar = ctk.CTkProgressBar(self.progress_frame, fg_color="#3F3F3F", progress_color="green", width=125, height=15, mode="determinate", border_width=1, border_color="green")
        self.progressbar.set(0)
        self.progressbar.pack(side="top", padx=8, pady=5)
        self.speedRemaining_time = ctk.CTkLabel(self.progress_frame, text="Ожидание...", text_color="grey")
        self.speedRemaining_time.pack(side="bottom", padx=2)
        self.progress_percent = ctk.CTkLabel(self.row_frame, text="0%", text_color="green")
        self.progress_percent.pack(side="left", padx=7)
        self.download_btn = ctk.CTkButton(self.row_frame, text="Скачать", fg_color="green", width=1, command=self.on_download_btn_pressed)
        self.download_btn.pack(side="left", padx=5, pady=5)
        self.stop_btn = ctk.CTkButton(self.row_frame, width=1, text="Стоп", fg_color="#76267a", state="disabled", command=self.on_stop_btn_pressed)
        self.stop_btn.pack(side="left", padx=5)
        self.del_row_btn = ctk.CTkButton(self.row_frame, text="X", fg_color="red", width=1, command=self._on_delete_btn_pressed)
        self.del_row_btn.pack(side='left', padx=5, pady=5)
    
    def set_download_callback(self, callback_function):
        self.on_download_click = callback_function

    def set_stop_callback(self, callback_function):
        self.on_stop_click = callback_function

    def set_delete_callback(self, callback_function):
        self.on_delete_click = callback_function

    def set_the_video_resolution(self, callback_function):
        self.save_video_qual = callback_function

    def handle_choose_video_qual_state(self, state):
        self.master_frame.after(0, lambda: self.choose_video_qual.configure(state=state))

    def reset_is_successfully_downloaded(self, callback_function):
        self.reset_flag_is_successfully_downloaded = callback_function

    def on_download_btn_pressed(self):
        if self.on_download_click:
            video_link = self.link_entry.get().strip()
            video_name = self.video_name.get().strip()
            self.on_download_click(video_link, video_name)
    
    def on_stop_btn_pressed(self):
        if self.on_stop_click:
            self.on_stop_click()

    def _on_delete_btn_pressed(self):
        if self.on_delete_click:
            self.on_delete_click()
    
    def _on_choose_video_qual(self, qual_value):
        if self.save_video_qual:
            self.save_video_qual(qual_value)

    def destroy_frame(self):
        self.row_frame.destroy()
        
    def lock_interface(self) -> None:
        self.master_frame.after(0, lambda: self.link_entry.configure(state="disabled"))
        self.master_frame.after(0, lambda: self.video_name.configure(state="disabled"))
        self.master_frame.after(0, lambda: self.download_btn.configure(state="disabled"))
        self.master_frame.after(0, lambda: self.del_row_btn.configure(state="disabled"))
        self.master_frame.after(0, lambda: self.stop_btn.configure(state="normal"))
        self.master_frame.after(0, lambda: self.speedRemaining_time.configure(text="В очереди...", text_color="grey"))

    def unlock_interface(self) -> None:
        self.master_frame.after(0, lambda: self.link_entry.configure(state="normal"))
        self.master_frame.after(0, lambda: self.video_name.configure(state="normal"))
        self.master_frame.after(0, lambda: self.download_btn.configure(state="normal"))
        self.master_frame.after(0, lambda: self.del_row_btn.configure(state="normal"))
        self.master_frame.after(0, lambda: self.stop_btn.configure(state="disabled"))

    def handle_progress(self, progress_float: float = None, percent_int: int = None, sec_time_val: str = None) -> None:
        if progress_float is not None and percent_int is not None:
            self.master_frame.after(0, self.progressbar.set, progress_float)
            self.master_frame.after(0, self.progress_percent.configure, text=f'{percent_int}%')
        if sec_time_val is not None:
            self.master_frame.after(0, self.speedRemaining_time.configure, text=sec_time_val)

    def handle_cancel(self, bar_value: float, percent_value:str, status_text: str, status_color:str):

        self.master_frame.after(0, self.progress_bar_and_percent_reset, bar_value, percent_value, status_text, status_color)
        self.master_frame.after(0, self.unlock_interface)

    def handle_error(self, error_msg: str = None, error_msg_mass: str = None) -> None:
        if error_msg is not None:
            self.master_frame.after(0, messagebox.showerror, "ОШИБКА", error_msg)
            self.master_frame.after(0, lambda: self.speedRemaining_time.configure(text="ОШИБКА", text_color="red"))
            self.master_frame.after(0, self.unlock_interface)
        if error_msg_mass is not None:
            self.master_frame.after(0, messagebox.showerror, "ОШИБКА", error_msg_mass)

    def on_typing_key_in_row(self, event):
        self.reset_flag_is_successfully_downloaded()
        self.master_frame.after(0, lambda: self.link_entry.configure(border_color = self.save_border_color))
        self.master_frame.after(0, lambda: self.speedRemaining_time.configure(text = "Ожидание...", text_color = "grey"))

    def handle_load_from_txt_link_and_name(self, link=None, name=None, bad_link=None):
        if bad_link is not None:
            self.master_frame.after(0, lambda: self.speedRemaining_time.configure(text=bad_link, text_color='red'))
            self.master_frame.after(0, lambda: self.link_entry.configure(border_color="red"))

        if link is not None and name is not None:
            self.master_frame.after(0, lambda: self.link_entry.insert(0, link))
            self.master_frame.after(0, lambda: self.video_name.insert(0, name))

    def progress_bar_and_percent_reset(self, bar_value: float, percent_value:str, status_text: str, status_color:str) -> None:
        self.master_frame.after(0, self.progressbar.set, bar_value)
        self.master_frame.after(0, self.progress_percent.configure, text=percent_value)
        self.master_frame.after(0, self.speedRemaining_time.configure, text=status_text, text_color=status_color)


class VideoTaskManager:
    def __init__(self, ui_row: VideoRowUI, setting: AppSetting, app_delete_callback, bytes_progress, on_status_change, current_mode):
        self.ui_row = ui_row
        self.settings = setting
        self.app_delete_callback = app_delete_callback
        self.bytes_progress = bytes_progress
        self.on_status_change = on_status_change
        self.current_mode = current_mode

        self._is_downloading = False
        self.is_successfully_downloaded = False
        self.is_stopped_by_user = False
        self.engine = False
        self.counter_lock = threading.Lock()

        self.current_link = ""
        self.current_vname = ""
        self.output_file = ""

        self.total_downloaded_bytes = 0


        self.ui_row.set_download_callback(self.preparing_to_download)
        self.ui_row.set_delete_callback(self.handle_delete_request)
        self.ui_row.reset_is_successfully_downloaded(self.reset_is_successfully_downloaded)
        self.ui_row.set_the_video_resolution(self.save_selected_video_quality)
        self.ui_row.set_stop_callback(self.stop_downloading)
    
    def check_if_ready_mass_download(self):
        self.is_stopped_by_user = False
        if self._is_downloading:
            return False
        if not self.ui_row.link_entry.get().strip() or not self.ui_row.video_name.get().strip():
            self.ui_row.handle_error(error_msg_mass="ЗАПОЛНИТЕ ВСЕ ПОЛЯ ДЛЯ ЗАГРУЗКИ ВИДЕО ФАЙЛОВ")
            return False
        if not self.settings['save_folder_path']:
             self.ui_row.handle_error(error_msg_mass="НЕ УКАЗАНА ПАПКА ДЛЯ СОХРАНЕНИЯ ВИДЕО")
             return False
        if self.current_mode() == "FFMPEG":
            if not self.settings['ffmpeg_path']:
                self.ui_row.handle_error(error_msg_mass="НЕ УКАЗАН ПУТЬ К FFMPEG")
                return False
        elif self.current_mode() == "YT-DLP":
            if not self.settings['yt_dlp_path']:
                self.ui_row.handle_error(error_msg_mass="НЕ УКАЗАН ПУТЬ К YT-DLP")
                return False
        self.current_link = self.ui_row.link_entry.get().strip()
        self.current_vname = re.sub(r'[\\/:*?"<>|]', "_", self.ui_row.video_name.get().strip())
        return True

    def preparing_to_download(self, video_link: str, video_name: str) -> None:
        if self.is_successfully_downloaded:
            self.ui_row.progress_bar_and_percent_reset(0, "0%", "Уже загружено", "blue")
            return
        if self._is_downloading:
            self.ui_row.handle_error("ПРОЦЕСС ЗАНЯТ")
            return
        if not video_link or not video_name:
            self.ui_row.handle_error("ЗАПОЛНИТЕ ВСЕ ПОЛЯ")
            return
        if not self.settings.get("save_folder_path", ""):
            self.ui_row.handle_error("НЕ ВЫБРАНА ПАПКА ДЛЯ СОХРАНЕНИЯ ВИДЕО")
            return
        current_mode = self.current_mode()
        if current_mode == "FFMPEG":
            if not self.settings['ffmpeg_path']:
                self.ui_row.handle_error("НЕ УКАЗАН ПУТЬ К FFMPEG")
                return
        elif current_mode == "YT-DLP":
            if not self.settings['yt_dlp_path']:
                self.ui_row.handle_error("НЕ УКАЗАН ПУТЬ К YT-DLP")
                return
        self.current_link = video_link
        self.current_vname = re.sub(r'[\\/:*?"<>|]', "_", video_name)
        self.is_stopped_by_user = False
        self._is_downloading = True
        self.ui_row.lock_interface()
        if self.on_status_change:
            self.on_status_change('disabled')

        threading.Thread(target=self.download_task, daemon=True).start()

    def lock_interface_for_mass_download(self):
        self.ui_row.lock_interface()
        if self.on_status_change:
            self.on_status_change('disabled')

    def download_task(self, open_folder: bool = True):
        if self.is_stopped_by_user:
            logger.warning("Скачивание видео отменено до начала загрузки")
            return
        self.output_file = os.path.join(self.settings.get('save_folder_path', ""), f"{self.current_vname}.mp4")
        current_mode = self.current_mode()
        logger.info(f'Начинается скачивание через {current_mode}. Файл {self.current_vname}')

        self.engine = DownloadEngine(
            on_progress=self.handle_progress,
            on_success=lambda: self.handle_success(open_folder=open_folder),
            on_error=self.handle_errors,
            on_cancel=self.handle_cancel
        )

        ffmpeg_path = self.settings.get("ffmpeg_path", "")

        if current_mode == 'FFMPEG':
            self.engine.download_via_ffmpeg(ffmpeg_path, self.current_link, self.output_file)
        elif current_mode == 'YT-DLP':
            yt_dlp_path = self.settings.get('yt_dlp_path', "")
            selected_quality = self.ui_row.choose_video_qual.get()
            quality_formats = {
                'HD4K': 'bestvideo[height<=2160]+bestaudio/best',
                'HQ2K': 'bestvideo[height<=1440]+bestaudio/best',
                '1080': 'bestvideo[height<=1080]+bestaudio/best',
                '720': 'bestvideo[height<=720]+bestaudio/best',
                '480': 'bestvideo[height<=480]+bestaudio/best',
                '360': 'bestvideo[height<=360]+bestaudio/best'
            }
            format_string = quality_formats.get(selected_quality, 'best')
            self.engine.download_via_yt_dlp(yt_dlp_path, self.current_link, format_string, self.output_file, ffmpeg_path) 

    def handle_progress(self, progress_float: float = None, percent_int: int = None, sec_time_val: str = None):
        if progress_float is not None and percent_int is not None:
            self.ui_row.handle_progress(progress_float, percent_int)
        if sec_time_val is not None:
            self.ui_row.handle_progress(sec_time_val=sec_time_val)

    def handle_success(self, open_folder: bool) -> None:
        self.is_successfully_downloaded = True

        add_to_history(self.current_vname, self.current_link, "Успешно")

        self.ui_row.progress_bar_and_percent_reset(1, "100", "Готово", "green")

        if os.path.exists(self.output_file):
            file_size = os.path.getsize(self.output_file)
            self.update_bytes_progress(file_size)

        if open_folder:
            self.open_folder_after_downloading()

        self._is_downloading = False

        self.ui_row.unlock_interface()
        if self.on_status_change:
            self.on_status_change('normal')

    def handle_errors(self, error_msg):
        self.ui_row.handle_error(error_msg)

    def handle_cancel(self,  bar_value: float, percent_value:str, status_text: str, status_color:str):

        self._is_downloading = False
        self.ui_row.handle_cancel(bar_value, percent_value, status_text, status_color)
        if self.on_status_change:
            self.on_status_change('normal')
            self.del_video_file_after_cancel()

    def handle_choose_video_qual_state(self, state):
        self.ui_row.handle_choose_video_qual_state(state)

    def stop_downloading(self):
        self.is_stopped_by_user = True
        if self.engine:
            self.engine.stop()
        else:
            if self.on_status_change:
                self.on_status_change('normal')
                self.ui_row.handle_cancel(0, "0%", "Ожидание...", "grey")

    def update_bytes_progress(self, new_bytes):
        with self.counter_lock:
            self.total_downloaded_bytes += new_bytes
            bytes_to_gb = self.total_downloaded_bytes / (1024**3)
            self.bytes_progress(bytes_to_gb)

    def open_folder_after_downloading(self) -> None:
        norm_path = os.path.normpath(self.output_file)
        if self.settings['save_folder_path'] and self.output_file:
            subprocess.Popen(f'explorer /select,{norm_path}')
        else:
            os.startfile(self.settings['save_folder_path'])

    def handle_delete_request(self):
        if self._is_downloading:
            return
        self.ui_row.destroy_frame()

        if self.app_delete_callback:
            self.app_delete_callback(self)

    def reset_is_successfully_downloaded(self):
        if self.is_successfully_downloaded:
            self.is_successfully_downloaded = False

    def save_selected_video_quality(self, qual_value):
        if self.settings:
            self.settings["selected_qual"] = qual_value
            save_setting(self.settings)

    def handle_load_from_txt_link_and_name(self, link, name):
        current_mode=self.current_mode()
        if current_mode == "FFMPEG":
            if not (link.startswith('http') and link.endswith('.m3u8')):
                self.ui_row.handle_load_from_txt_link_and_name(bad_link = "Неверный формат ссылки")
            self.ui_row.handle_load_from_txt_link_and_name(link, name)
        else:
            self.ui_row.handle_load_from_txt_link_and_name(link, name)

    def handle_progress_bar_and_percent_reset_from_App(self, bar_value: float, percent_value:str, status_text: str, status_color:str):
        self.ui_row.progress_bar_and_percent_reset(bar_value, percent_value, status_text, status_color)

    def del_video_file_after_cancel (self):
        dirname = os.path.dirname(self.output_file)
        list_dir = os.listdir(dirname)
        for file in list_dir:
            if file.startswith(f'{self.current_vname}'):
                file_path = os.path.join(dirname, file)
                os.remove(file_path)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("M3U8 Downloader")
        self.setting = load_setting()
        self.ffmpeg_path = self.setting.get('ffmpeg_path', "")
        self.save_folder_path = self.setting.get('save_folder_path', "")
        self.yt_dlp_path = self.setting.get('yt_dlp_path', "")
        self.download_method = self.setting.get('download_method', "FFMPEG")
        self.rows_count = self.setting.get('rows_count', 1)
        self.all_rows: list[VideoTaskManager] = []
        self.total_downloaded_bytes = 0
        self.stop_all_downloads = threading.Event()

        self.geometric_calculation(1150, 650)
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing_app)

        self.to_queue_manager = DownloadQueueManager(
            stop_all = self.handle_cancel_all
        )

        if self.ffmpeg_path:
            self.choose_ffmpeg_btn.configure(border_color="green")
        if self.yt_dlp_path:
            self.choose_yt_dlp_btn.configure(border_color="green")

        for _ in range(self.rows_count):
            self.add_new_row()

        if self.download_method == "YT-DLP":        
            self.choose_download_option.set("YT-DLP")
            for row in self.all_rows:
                row.handle_choose_video_qual_state(state="normal")
        else:
            self.choose_download_option.set("FFMPEG")
            for row in self.all_rows:
                row.handle_choose_video_qual_state(state='disabled')

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
            save_setting(self.setting)

    def choose_ffmpeg_path(self):
        user_path = filedialog.askopenfilename(title="Укажите путь к FFmpeg", filetypes=[("ffmpeg.exe", "ffmpeg.exe")])
        if user_path:
            self.ffmpeg_path = user_path
            self.choose_ffmpeg_btn.configure(border_color="green")
            self.setting['ffmpeg_path'] = self.ffmpeg_path
            save_setting(self.setting)
                                           
    def choose_yt_dlp_path(self):
        user_path = filedialog.askopenfilename(title="Укажите путь к файлу запуска yt-dlp", filetypes=[('yt-dlp.exe', 'yt-dlp.exe')])
        if user_path:
            self.yt_dlp_path = user_path
            self.choose_yt_dlp_btn.configure(border_color="green")
            self.setting['yt_dlp_path'] = self.yt_dlp_path
            save_setting(self.setting)

    def selected_download_method(self, event):
        self.setting['download_method'] = event
        save_setting(self.setting)
        if event == "FFMPEG":
            for row in self.all_rows:
                row.handle_choose_video_qual_state(state="disabled")
        else:
            for row in self.all_rows:
                row.handle_choose_video_qual_state(state='normal')
    
    def save_selected_qual_task(self, data):
        self.setting['selected_qual'] = data
        save_setting(self.setting)

    def change_global_buttn(self, button_state):
        if button_state == "normal":
            if any(row._is_downloading for row in self.all_rows):
                return
        self.after(0, lambda: self.download_sequence_btn.configure(state=button_state))
        self.after(0, lambda: self.download_all_btn.configure(state=button_state))
        self.after(0, lambda: self.delete_all_rows_btn.configure(state=button_state))
    
    def remove_from_all_rows(self, task_manager):
        self.all_rows.remove(task_manager)
        self.calc_rows()

    def delete_all_rows(self):
        for row in self.all_rows[:]:
            row.handle_delete_request()
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
        self.load_txt_btn = ctk.CTkButton(self.first_btn_frame, text="ИМПОРТ ИЗ TXT", font=("Arial", 14, "bold"), width=150, command=self.load_from_txt_filedialog)
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
    
    def calc_rows(self):
        count_of_rows = len(self.all_rows)
        self.setting['rows_count'] = count_of_rows
        save_setting(self.setting)

    def load_from_txt_filedialog(self):

        file_path = filedialog.askopenfilename(title="Выберите файл с данными", filetypes=[('Text files', '*.txt')])

        if not file_path:
            return

        pair_up_lines = parse_txt_file(file_path)

        for row in self.all_rows[:]:
            row.handle_delete_request()

        for link, name in pair_up_lines:
            self.add_new_row()
            last_row = self.all_rows[-1]
            last_row.handle_load_from_txt_link_and_name(link, name)

    def add_new_row(self):
        default_quality = self.setting.get('selected_qual', '1080')
        
        new_row_ui = VideoRowUI(self.main_frame, default_qual=default_quality)
        video_task_manager = VideoTaskManager(ui_row=new_row_ui,    
                                              setting=self.setting,
                                              app_delete_callback = self.remove_from_all_rows,
                                              bytes_progress = self.update_bytes_progress,
                                              on_status_change = self.change_global_buttn,
                                              current_mode = self.choose_download_option.get
                                              )
        self.all_rows.append(video_task_manager)
        self.calc_rows()

    def update_bytes_progress(self, new_bytes):

        self.total_downloaded_bytes_label.configure(text=f'Всего загружено: {new_bytes:.2f} ГБ')

    def pre_download_check(self):
        for row in self.all_rows:
            if not row.check_if_ready_mass_download():
                return False
        for row in self.all_rows:
            if not row.is_successfully_downloaded:
                row.lock_interface_for_mass_download()
        return True
    
    def download_sequence(self):
        if not self.pre_download_check():
            return
        threading.Thread(target=self._download_sequence_thread, daemon=True).start()

    def _download_sequence_thread(self):
        for row in self.all_rows:
            if self.stop_all_downloads.is_set():
                return
            if not row.is_successfully_downloaded:
                row.download_task(open_folder=False)
        if any (row.is_successfully_downloaded for row in self.all_rows):
            self.open_folder_task()

    def start_download_all(self):
        threading.Thread(target=self.add_to_queue, daemon=True).start()

    def add_to_queue(self):
        if not self.pre_download_check():
            return
        task_added = False

        for row in self.all_rows:
            if not row.is_successfully_downloaded:
                self.to_queue_manager.add_to_queue_task(row)
                task_added = True
            else:
                row.handle_progress_bar_and_percent_reset_from_App(1, "100%", "Уже скачано", "red")

        if task_added:
            self.to_queue_manager.wait_all_tasks()
            if any(row.is_successfully_downloaded for row in self.all_rows):
                self.open_folder_task()

    def stop_all_downloads_task(self):
        self.stop_all_downloads.set()
        self.to_queue_manager.stop_downloads()

    def handle_cancel_all(self):

        for row in self.all_rows:
            row.stop_downloading()

    def on_closing_app(self):
        
        self.stop_all_downloads_task()
        
        self.destroy()

# region СТАРЫЙ МНОГОПОТОЧНЫЙ РЕЖИМ (НЕ ИСПОЛЬЗУЕТСЯ)
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