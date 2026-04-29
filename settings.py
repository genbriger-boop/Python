from typing import TypedDict
import os
import json
from dataclasses import dataclass
from dataclasses import asdict

@dataclass
class AppSetting:
    ffmpeg_path: str
    save_folder_path: str
    yt_dlp_path: str
    download_method: str
    selected_qual: str
    rows_count: int

    def save(self) -> None:
        with open (current_path, "w", encoding="utf-8") as file:
            json.dump(asdict(self), file, ensure_ascii=False, indent=4)

file_name = 'settings.json'
dir_name = os.path.dirname(__file__)
current_path = os.path.join(dir_name, file_name)

DEFAULT_SETTING = AppSetting(
     ffmpeg_path = "",
     save_folder_path = "",
     yt_dlp_path = "",
     download_method = "FFMPEG",
     selected_qual = "1080",
     rows_count = 1
)

def load_setting() -> AppSetting:
        if os.path.exists(current_path):
            try:
                with open (current_path, "r", encoding="utf-8") as file:
                    raw_data = json.load(file)
                    return AppSetting(**raw_data)
            except json.JSONDecodeError:
                return DEFAULT_SETTING
            
        return DEFAULT_SETTING