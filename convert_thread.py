"""convert_thread.py

"""

import sys
import threading
import os


class ConvertThread(threading.Thread):

    def __init__(self, queue, out_queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.out_queue = out_queue
        return


    def run(self):
        while True:
            class_instance, process, file_in, file_out, overwrite = \
                self.queue.get()

            error = None
            try:
                if overwrite or not os.path.isfile(file_out):
                    process(file_in, file_out)

                else:
                    error = (
                        "File not converted:"
                        " file already exists and overwrite is set to False."
                    )

            except Exception as e:
                error = str(e)

            self.out_queue.put((file_in, file_out, error))
            self.queue.task_done()

        return
