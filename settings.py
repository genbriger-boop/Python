from typing import TypedDict
import os
import json

class AppSetting(TypedDict):
    ffmpeg_path: str
    save_folder_path: str
    yt_dlp_path: str
    download_method: str
    selected_qual: str
    rows_count: int

setting_file = "settings.json"
DEFAULT_SETTING: AppSetting = {
     'ffmpeg_path': "",
     'save_folder_path': "",
     'yt_dlp_path': "",
     'download_method': "FFMPEG",
     'selected_qual': "1080",
     'rows_count': 1
}

def load_setting() -> AppSetting:
        if os.path.exists(setting_file):
            try:
                with open (setting_file, "r", encoding="utf-8") as file:
                    return json.load(file)
            except json.JSONDecodeError:
                return DEFAULT_SETTING
            
        return DEFAULT_SETTING

def save_setting(data: AppSetting) -> None:
        with open (setting_file, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)