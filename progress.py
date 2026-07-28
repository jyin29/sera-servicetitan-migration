class Progress:

    def __init__(self):

        self.gui = None

    def attach_gui(self, gui):

        self.gui = gui

    def log(self, message):

        print(message)

        #if self.gui:
        #    self.gui.write(message + "\n")

    def customer(self, customer_id):

        #print("customer() called")
        #print("gui =", self.gui)

        if self.gui:
            #print("calling set_customer")
            self.gui.set_customer(customer_id)

    def job(self, job_number):

        if self.gui:

            self.gui.set_job(job_number)

    def file(self, filename):

        if self.gui:

            self.gui.set_file(filename)

    def uploaded(self, count):

        if self.gui:

            self.gui.set_uploaded(count)

    def skipped(self, count):

        if self.gui:

            self.gui.set_skipped(count)

    def failed(self, count):

        if self.gui:

            self.gui.set_failed(count)

    def progress(self, current, total):

        if self.gui:

            self.gui.set_progress(current, total)

    def elapsed(self, text):

        if self.gui:

            self.gui.set_elapsed(text)

    def eta(self, text):

        if self.gui:

            self.gui.set_eta(text)

    def action(self, text):

        if self.gui:

            self.gui.set_action(text)

    def progress_unit(self, text):

        if self.gui:
            self.gui.set_progress_unit(text)


progress = Progress()