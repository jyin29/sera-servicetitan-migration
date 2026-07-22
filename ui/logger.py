import io
import sys


class GuiLogger(io.TextIOBase):

    def __init__(self, callback):
        self.callback = callback

    def write(self, text):

        if text:
            self.callback(text)

        return len(text)

    def flush(self):
        pass


class StdoutRedirect:

    def __init__(self, callback):

        self.callback = callback

        self.original_stdout = sys.stdout

        self.logger = GuiLogger(callback)

    def start(self):

        sys.stdout = self.logger

    def stop(self):

        sys.stdout = self.original_stdout