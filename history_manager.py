import json
import os
import threading
from datetime import datetime
from collections import deque

file_path = "history.json"
dir_name = os.path.dirname(__file__)
history_file = os.path.join(dir_name, file_path)

class HistoryManager:
    def __init__(self):
        self.history_lock = threading.Lock()
        self.history_data = self.load_history()

    def load_history(self):

        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    return deque(data, maxlen=50)
            except json.JSONDecodeError:
                return deque(maxlen=50)
        return deque(maxlen=50)

    def add_to_history(self, file_name, url, status):

        with self.history_lock:

            new_entry = {
                'name': file_name,
                'url': url,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                "status": status
            }
            self.history_data.appendleft(new_entry)
            #region ДОБАВЛЯЛ НА ПЕРВУЮ ПОЗИЦИЮ КОГДА ИСПОЛЬЗОВАЛ СПИСОК (НЕ ИСПОЛЬЗУЮ УЖЕ)
            #self.history_data.insert(0, new_entry)
            #self.history_data = self.history_data[:50]
            #endregion

    def save(self):

        with open(history_file, 'w', encoding='utf-8') as file:
                json.dump(list(self.history_data), file, ensure_ascii=False, indent=4)