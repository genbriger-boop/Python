import json
import os
import threading
from datetime import datetime

history_file = "history.json"
history_lock = threading.Lock()

def add_to_history(file_name, url, status):
        
        with history_lock:
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r', encoding='utf-8') as file:
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

            with open(history_file, 'w', encoding='utf-8') as file:
                json.dump(history_data, file, ensure_ascii=False, indent=4)