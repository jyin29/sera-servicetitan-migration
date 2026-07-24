from ui.logger import StdoutRedirect
import customtkinter as ctk
import threading
import traceback
from tkinter import filedialog
from test_sera import run as sera_download



class MainWindow:

    def __init__(self):

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()

        self.root.title("Sera → ServiceTitan Migration")

        self.root.geometry("900x650")

        self.build()

        self.stdout = StdoutRedirect(self.write)

    def build(self):

        title = ctk.CTkLabel(
            self.root,
            text="Sera → ServiceTitan Migration",
            font=("Segoe UI", 26, "bold")
        )

        title.pack(pady=30)

        self.start_button = ctk.CTkButton(
            self.root,
            text="Run Full Migration",
            width=400,
            height=50,
            font=("Segoe UI", 18, "bold"),
            command=self.start_clicked
        )

        self.start_button.pack(pady=(0, 20))

        self.download_button = ctk.CTkButton(
            self.root,
            text="Download Media From Sera",
            width=300,
            height=40,
            command=self.download_clicked
        )

        self.download_button.pack(pady=10)

        self.manifest_button = ctk.CTkButton(
            self.root,
            text="Generate Manifest",
            width=300,
            height=40,
            command=self.manifest_clicked
        )

        self.manifest_button.pack(pady=10)

        self.upload_button = ctk.CTkButton(
            self.root,
            text="Upload To ServiceTitan",
            width=300,
            height=40,
            command=self.upload_clicked
        )

        self.upload_button.pack(pady=10)

        status_frame = ctk.CTkFrame(self.root)

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

        self.log = ctk.CTkTextbox(
            self.root,
            width=760,
            height=350
        )

        self.log.configure(state="disabled")

        self.log.pack(pady=25)

        self.write("Application started.\n")

    def write(self, text):

        self.log.configure(state="normal")

        self.log.insert("end", text)

        self.log.see("end")

        self.log.configure(state="disabled")

    def set_status(self, text):

        self.root.after(
            0,
            lambda: self.status_label.configure(
                text=f"Status: {text}"
            )
        )

    def set_customer(self, text):

        self.root.after(
            0,
            lambda: self.customer_label.configure(
                text=f"Customer: {text}"
            )
        )


    def set_job(self, text):

        self.root.after(
            0,
            lambda: self.job_label.configure(
                text=f"Job: {text}"
            )
        )


    def set_file(self, text):

        self.root.after(
            0,
            lambda: self.file_label.configure(
                text=f"File: {text}"
            )
        )

    def start_clicked(self):

        self.write("Starting full migration...\n")

        thread = threading.Thread(
            target=self.run_full_migration,
            daemon=True
        )

        thread.start()

    def download_clicked(self):

        self.write("Starting Sera downloader...\n")

        thread = threading.Thread(
            target=self.run_downloader,
            daemon=True
        )

        thread.start()

    def run_downloader(self):

        self.stdout.start()

        try:

            sera_download()

            print("\nDownload complete.")

        except Exception:

            print(traceback.format_exc())

        finally:

            self.stdout.stop()

    def run_full_migration(self):

        self.set_status("DOWNLOADING")

        self.stdout.start()

        try:

            print("=" * 60)
            print("STEP 1")
            print("Downloading from Sera...")
            print("=" * 60)

            sera_download()

            print()
            print("=" * 60)
            print("STEP 2")
            print("Uploading to ServiceTitan...")
            print("=" * 60)

            from migration_engine import MigrationEngine

            self.set_status("UPLOADING")

            MigrationEngine().run()

            self.set_status("FINISHED")

            print()
            print("Migration complete.")

        except Exception:

            print(traceback.format_exc())

            self.set_status("FAILED")

        finally:

            self.stdout.stop()

    def manifest_clicked(self):
        self.write("Generate Manifest clicked.\n")

    def upload_clicked(self):
        thread = threading.Thread(
            target=self.run_upload,
            daemon=True
        )

        thread.start() 

    def run_upload(self):

        self.stdout.start()

        try:

            from migration_engine import MigrationEngine

            MigrationEngine().run()

        except Exception:

            print(traceback.format_exc())

        finally:

            self.stdout.stop()

    def run(self):
        self.root.mainloop()