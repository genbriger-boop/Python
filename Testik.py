import customtkinter as ctk
import json
import os
from tkinter import messagebox
from dataclasses import dataclass
from dataclasses import asdict
from collections import deque
from datetime import datetime


settings = "settingsss.json"

@dataclass
class AppSetting:
    selected_format: str

    def save_setting(self):
        with open(settings, 'w', encoding='utf-8') as file:
            json.dump(asdict(self), file, ensure_ascii=False, indent=4)

DEFAULT_SETTING = AppSetting(
    selected_format = "TXT"
)

def load_setting():
    if os.path.exists(settings):
        try:
            with open(settings, 'r', encoding='utf-8') as file:
                raw_data = json.load(file)
                return AppSetting(**raw_data)
        except json.JSONDecodeError:
            return DEFAULT_SETTING
    else:
        return DEFAULT_SETTING
    

class Splitter:
    format_name = None
    def save_file(self, label, text, file_name, current_time):
        raise NotImplementedError("Не там указал")

class SaveTxt(Splitter):
    format_name = 'TXT'
    def save_file(self, label, text, file_name, current_time):
        with open(f'{file_name}.txt', 'a', encoding='utf-8') as file:
            file.write(f'\n\nОтчёт сгенерирован: {current_time}\n\nЗаголовок: {label}\n\nТекст: {text}')
        

class SaveJson(Splitter):
    format_name = 'JSON'
    def save_file(self, label, text, file_name, current_time):

        file_path = f'{file_name}.json'
        data = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
            except json.JSONDecodeError:
                data = []
                
        
        deque_data = deque(data, maxlen=2)

        deque_data.appendleft({
            'current_time': current_time,
            'label': label,
            'text': text
        })

        with open(f'{file_name}.json', 'w', encoding='utf-8') as file:
            json.dump(list(deque_data), file, ensure_ascii=False, indent=4)

class SaveHtml(Splitter):
    format_name = 'HTML'
    def save_file(self, label, text, file_name, current_time):
        with open(f'{file_name}.html', "a", encoding='utf-8') as file:
            file.write(f'\n\nОтчёт сгенерирован: {current_time}<h1>{label}</h1><p>{text}</p>')

class SaveMd(Splitter):
    format_name = 'MD'
    def save_file(self, label, text, file_name, current_time):
        with open(f'{file_name}.md', 'w', encoding='utf-8') as file:
            file.write(f'\n\nОтчёт сгенерирован: {current_time}\n# {label}\n{text}')

class PrintInTerminal(Splitter):
    format_name = 'Console'
    def save_file(self, label, text, file_name, current_time):
        print(f'\n\nОтчёт сгенерирован: {current_time} Имя файла: {file_name}, Заголовок: {label}, Текст: {text}')

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Универсальный генератор отчетов")
        self.geometry('900x600')

        self.main_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.main_frame.pack(expand=True)
        prepeare_the_formats = Factory.get_available_formats()
        self.select_format = ctk.CTkOptionMenu(self.main_frame, values=prepeare_the_formats, width=50, command=self.take_selected_method)
        self.select_format.pack(pady=5)
        self.report_title_label = ctk.CTkLabel(self.main_frame, text="Введите заголовок отчёта:")
        self.report_title_label.pack(pady=5)
        self.report_title_entry = ctk.CTkEntry(self.main_frame, width=300)
        self.report_title_entry.pack(pady=5)
        self.report_text_label = ctk.CTkLabel(self.main_frame, text="Введите текст отчёта:")
        self.report_text_label.pack(pady=5)
        self.report_text_entry = ctk.CTkEntry(self.main_frame, width=300)
        self.report_text_entry.pack(pady=5)
        self.report_name_label = ctk.CTkLabel(self.main_frame, text="Введите имя отчёта")
        self.report_name_label.pack(pady=5)
        self.report_name_entry = ctk.CTkEntry(self.main_frame, width=300)
        self.report_name_entry.pack(pady=5)
        self.save_report_btn = ctk.CTkButton(self.main_frame, text="Сохранить отчёт", command=self.extracting_data)
        self.save_report_btn.pack(pady=30)

        self.file_name = ""
        self.settings = load_setting()
        self.current_method = self.settings.selected_format
        self.select_format.set(self.current_method)

        build_obj = Factory.creating_object(self.current_method)
        self.worker = Worker(build_obj)

    def handle_error(self, error):
        self.after(0, messagebox.showerror, "Ошибка", error)

    def clear_rows(self):
        self.report_title_entry.delete(0, 'end')
        self.report_text_entry.delete(0, 'end')
        self.report_name_entry.delete(0, 'end')

    def extracting_data(self):

        report_label = self.report_title_entry.get().strip()
        report_text = self.report_text_entry.get().strip()
        report_name = self.report_name_entry.get().strip()
        now = datetime.now()
        current_time = now.strftime('%Y-%m-%d-%H:%M:%S')

        if report_name:
            self.file_name = report_name
        else:
            self.file_name = f'report_{now.strftime('%Y_%m_%d_%H_%M_%S')}'

        if not report_label or not report_text:
            self.handle_error("Заполните все поля")
            return

        self.worker.send_to_obj(report_label, report_text, self.file_name, current_time)

        self.clear_rows()

    def take_selected_method(self, selected_method):
        build_obj = Factory.creating_object(selected_method)
        self.worker.set_save_obj(build_obj)
        self.settings.selected_format = selected_method
        self.settings.save_setting()
        
class Factory:
    _cached_formats = None
    @classmethod
    def creating_object(cls, method):

        get_list = cls.get_all_formats()
        creat_obj = get_list.get(method)
        return creat_obj()
    
    @classmethod
    def get_available_formats(cls):
        
        get_list = cls.get_all_formats()
        return list(get_list.keys())
    
    @classmethod
    def get_all_formats(cls):
        if cls._cached_formats is None:
            formats = {}
            for subclass in Splitter.__subclasses__():
                if subclass.format_name is not None:
                    formats[subclass.format_name] = subclass
                    
            cls._cached_formats = formats
        
        return cls._cached_formats
        

class Worker:
    def __init__(self, current_obj: Splitter):

        self.set_save_obj(current_obj)

    def set_save_obj(self, obj: Splitter):

        if hasattr(obj, 'save_file') and callable(getattr(obj, 'save_file')):
            self.save_obj = obj
        else:
            raise TypeError("Этот объект не подходит! Он не умеет сохранять файлы (нет метода save_file).")

    def send_to_obj(self, report_label, report_text, file_name, current_time):
        
        self.save_obj.save_file(report_label, report_text, file_name, current_time)
print()
if __name__ == '__main__':
    app = App()
    app.mainloop()
