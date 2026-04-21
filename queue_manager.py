import queue
import threading


class DownloadQueueManager:
    def __init__(self, stop_all):
        self.stop_all_downloads = threading.Event()
        self.queue_box = queue.Queue()
        self.stop_all = stop_all
        for _ in range(3):
            threading.Thread(target=self.queue_download_task, daemon=True).start()

    def add_to_queue_task(self, row):

        self.stop_all_downloads.clear()
        self.queue_box.put(row)


    def queue_download_task(self):
        while True:
            get_task = self.queue_box.get()

            if self.stop_all_downloads.is_set():
                self.queue_box.task_done()
                continue
            
            get_task.download_task(open_folder = False)
            self.queue_box.task_done()
    

    def wait_all_tasks(self):

        self.queue_box.join()


    def stop_downloads(self):
        self.stop_all_downloads.set()

        while not self.queue_box.empty():
            try:
                self.queue_box.get_nowait()
                self.queue_box.task_done()
            except queue.Empty:
                break
        
        self.stop_all()
        