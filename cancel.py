class CancelToken:

    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def reset(self):
        self.cancelled = False

    def is_cancelled(self):
        return self.cancelled


cancel = CancelToken()