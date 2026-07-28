from ui.logger import StdoutRedirect
from pathlib import Path
import customtkinter as ctk
import threading
import traceback
from tkinter import filedialog, ttk, messagebox
from test_sera import run
import time
from datetime import datetime, timedelta

class MainWindow:

    def __init__(self):

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()

        self.root.title("Sera → ServiceTitan Migration")

        self.root.geometry("1100x950")

        self.container = ctk.CTkScrollableFrame(self.root)
        self.container.pack(fill="both", expand=True)

        self.build()

        self.stdout = StdoutRedirect(self.write)

        from progress import progress
        
        progress.attach_gui(self)

        self.migration_start = None

        self.timer_running = False

        self.progress_current = 0

        self.progress_total = 0

        self.progress_unit = "Customers"

    def cancel_clicked(self):

        from cancel import cancel

        cancel.cancel()

        self.set_status("CANCELLING...")

    def set_progress(
        self,
        current,
        total
    ):

        self.progress_current = current

        self.progress_total = total

        def update():

            self.progress["maximum"] = total

            self.progress["value"] = current

            self.progress_label.configure(
                text=f"{current} / {total} {self.progress_unit}"
            )

            if total > 0:
                percent = int(current / total * 100)
            else:
                percent = 0

            self.percent_label.configure(
                text=f"{percent}%"
            )

        self.root.after(0, update)

    def build(self):

        title = ctk.CTkLabel(
            self.container,
            text="Sera → ServiceTitan Migration",
            font=("Segoe UI", 26, "bold")
        )

        title.pack(pady=30)

        self.workbook_label = ctk.CTkLabel(
            self.container,
            text="Workbook: None",
            font=("Segoe UI", 12)
        )

        self.workbook_label.pack(
            pady=(0, 15)
        )

        #
        # Progress
        #
        self.progress = ttk.Progressbar(
            self.container,
            orient="horizontal",
            mode="determinate",
        )

        self.progress.pack(
            fill="x",
            padx=20,
            pady=(5, 10)
        )

        self.progress_label = ctk.CTkLabel(
            self.container,
            text="0 / 0 Customers"
        )

        self.progress_label.pack()

        self.percent_label = ctk.CTkLabel(
            self.container,
            text="0%"
        )

        self.percent_label.pack()

        #
        # Excel workbook
        #
        self.excel_path = ctk.StringVar(
            value="exports/CustomerContactReport-2026-07-22-58a68e.xlsx"
        )

        self.workbook_label.configure(
            text=f"Workbook: {Path(self.excel_path.get()).name}"
        )

        excel_frame = ctk.CTkFrame(self.container)

        excel_frame.pack(
            pady=(0, 20),
            padx=20,
            fill="x"
        )

        ctk.CTkLabel(
            excel_frame,
            text="Customer Export"
        ).pack(
            side="left",
            padx=10
        )

        self.excel_entry = ctk.CTkEntry(
            excel_frame,
            textvariable=self.excel_path
        )

        self.excel_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=10
        )

        ctk.CTkButton(
            excel_frame,
            text="Browse",
            width=90,
            command=self.pick_excel
        ).pack(
            side="right",
            padx=10
        )

        self.limit_label = ctk.CTkLabel(
            self.container,
            text="Customers to Process (0 = All)"
        )

        self.limit_label.pack()

        self.limit_entry = ctk.CTkEntry(
            self.container,
            width=120
        )

        self.limit_entry.insert(0, "1")

        self.limit_entry.pack(pady=(0, 20))

        button_frame = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )

        button_frame.pack(pady=(10, 20))

        self.start_button = ctk.CTkButton(
            button_frame,
            text="Run Full Migration",
            width=400,
            height=50,
            font=("Segoe UI", 18, "bold"),
            command=self.start_clicked
        )

        self.start_button.pack(
            side="left",
            padx=10
        )

        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=150,
            command=self.cancel_clicked
        )

        self.cancel_button.pack(
            side="left",
            padx=10
        )        

        status_frame = ctk.CTkFrame(self.container)

        status_frame.pack(
            fill="x",
            padx=40,
            pady=(20, 10)
        )

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Status: READY",
            font=("Segoe UI", 16, "bold")
        )

        self.status_label.pack(
            anchor="w",
            padx=15,
            pady=(10, 0)
        )

        self.action_label = ctk.CTkLabel(
            status_frame,
            text="Action: Waiting..."
        )

        self.action_label.pack(
            anchor="w",
            padx=15
        )

        self.customer_label = ctk.CTkLabel(
            status_frame,
            text="Customer: -"
        )

        self.customer_label.pack(
            anchor="w",
            padx=15
        )

        self.job_label = ctk.CTkLabel(
            status_frame,
            text="Job: -"
        )

        self.job_label.pack(
            anchor="w",
            padx=15
        )

        self.file_label = ctk.CTkLabel(
            status_frame,
            text="File: -"
        )

        self.file_label.pack(
            anchor="w",
            padx=15,
            pady=(0, 10)
        )

        #
        # Statistics
        #
        stats_frame = ctk.CTkFrame(self.container)

        stats_frame.pack(
            fill="x",
            padx=40,
            pady=(0, 10)
        )

        #
        # Left column
        #

        left = ctk.CTkFrame(
            stats_frame,
            fg_color="transparent"
        )

        left.pack(
            side="left",
            padx=20,
            anchor="n"
        )

        self.uploaded_label = ctk.CTkLabel(
            left,
            text="Uploaded: 0"
        )
        self.uploaded_label.pack(anchor="w")

        self.skipped_label = ctk.CTkLabel(
            left,
            text="Skipped: 0"
        )
        self.skipped_label.pack(anchor="w")

        self.failed_label = ctk.CTkLabel(
            left,
            text="Failed: 0"
        )
        self.failed_label.pack(anchor="w")

        #
        # Right column
        #

        right = ctk.CTkFrame(
            stats_frame,
            fg_color="transparent"
        )

        right.pack(
            side="right",
            padx=(80,20),
            anchor="n"
        )

        self.elapsed_label = ctk.CTkLabel(
            right,
            text="Elapsed: 00:00:00"
        )

        self.elapsed_label.pack(anchor="e")

        self.eta_label = ctk.CTkLabel(
            right,
            text="ETA: --"
        )

        self.eta_label.pack(anchor="e")

        self.log = ctk.CTkTextbox(
            self.container,
            height=350
        )

        self.log.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self.log.configure(state="disabled")

        self.write("Application started.\n")

    def write(self, text):

        self.log.configure(state="normal")

        self.log.insert("end", text)

        self.log.see("end")

        self.log.configure(state="disabled")

    def pick_excel(self):

        filename = filedialog.askopenfilename(

            title="Select Customer Export",

            filetypes=[
                (
                    "Excel Workbook",
                    "*.xlsx"
                )
            ]
        )

        if filename:

            self.excel_path.set(filename)    

        self.workbook_label.configure(
            text=f"Workbook: {Path(filename).name}"
        )

    def set_status(self, text):

        self.root.after(
            0,
            lambda: self.status_label.configure(
                text=f"Status: {text}"
            )
        )

    def set_customer(self, customer):

        self.root.after(
            0,
            lambda: self.customer_label.configure(
                text=f"Customer: {customer}"
            )
        )


    def set_job(self, job):

        self.root.after(
            0,
            lambda: self.job_label.configure(
                text=f"Job: {job}"
            )
        )

    def set_file(self, text):

        self.root.after(
            0,
            lambda: self.file_label.configure(
                text=f"File: {text}"
            )
        )

    def set_uploaded(self, count):

        self.uploaded = count

        self.root.after(
            0,
            lambda: self.uploaded_label.configure(
                text=f"Uploaded: {count}"
            )
        )


    def set_skipped(self, count):

        self.skipped = count

        self.root.after(
            0,
            lambda: self.skipped_label.configure(
                text=f"Skipped: {count}"
            )
        )


    def set_failed(self, count):

        self.failed = count

        self.root.after(
            0,
            lambda: self.failed_label.configure(
                text=f"Failed: {count}"
            )
        )

    def set_elapsed(self, text):

        self.root.after(
            0,
            lambda: self.elapsed_label.configure(
                text=f"Elapsed: {text}"
            )
        )


    def set_eta(self, text):

        self.root.after(
            0,
            lambda: self.eta_label.configure(
                text=f"ETA: {text}"
            )
        )

    def start_clicked(self):

        self.write("Starting full migration...\n")

        thread = threading.Thread(
            target=self.run_full_migration,
            daemon=True
        )

        thread.start()

    def set_action(self, text):

        self.root.after(
            0,
            lambda: self.action_label.configure(
                text=f"Action: {text}"
            )
        )

    def set_progress_unit(self, text):

        def update():
            self.progress_unit = text

        self.root.after(0, update)

    def update_elapsed_timer(self):

        if not self.timer_running:
            return

        elapsed = time.time() - self.migration_start

        if self.progress_current > 0:

            average = elapsed / self.progress_current

            remaining = self.progress_total - self.progress_current

            eta_seconds = average * remaining

            eta = datetime.now() + timedelta(seconds=eta_seconds)

            self.eta_label.configure(
                text=f"ETA: {eta.strftime('%I:%M:%S %p')}"
            )

        self.elapsed_label.configure(
            text=f"Elapsed: {timedelta(seconds=int(elapsed))}"
        )

        self.root.after(250, self.update_elapsed_timer)

    def run_full_migration(self):

        from cancel import cancel

        from progress import progress

        cancel.reset()

        self.migration_start = time.time()
        self.timer_running = True

        self.root.after(0, self.update_elapsed_timer)

        self.set_status("DOWNLOADING")

        self.stdout.start()

        try:

            progress.progress_unit("Customers")

            print("=" * 60)
            print("STEP 1")
            print("Downloading from Sera...")
            print("=" * 60)

            limit = int(self.limit_entry.get())

            run(
                workbook=self.excel_path.get(),
                limit=limit
            )

            progress.progress_unit("Jobs")

            print()
            print("=" * 60)
            print("STEP 2")
            print("Uploading to ServiceTitan...")
            print("=" * 60)

            from migration_engine import MigrationEngine

            self.set_status("UPLOADING")

            MigrationEngine().run()

            self.set_status("FINISHED")

            messagebox.showinfo(

                "Migration Complete",

                f"""
            Migration Complete!

            Uploaded : {self.uploaded_var.get()}
            Skipped  : {self.skipped_var.get()}
            Failed   : {self.failed_var.get()}

            Any failed files have been moved to:

            failed_media/

            for manual upload.
            """
            )

            print()
            print("Migration complete.")

        except Exception as e:

            import traceback

            traceback.print_exc()

            print("\nEXCEPTION:")
            print(repr(e))

            self.set_status("FAILED")

            messagebox.showerror(
                "Migration Failed",
                str(e)
            )

        finally:

            self.timer_running = False

            self.stdout.stop()

    def run(self):

        self.root.mainloop()