from ui.logger import StdoutRedirect
import customtkinter as ctk
import threading
import traceback
from tkinter import filedialog
from test_sera import run



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

        #
        # Excel workbook
        #
        self.excel_path = ctk.StringVar(
            value="exports/CustomerContactReport.xlsx"
        )

        excel_frame = ctk.CTkFrame(self.root)

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
            self.root,
            text="Customers to Process (0 = All)"
        )

        self.limit_label.pack()

        self.limit_entry = ctk.CTkEntry(
            self.root,
            width=120
        )

        self.limit_entry.insert(0, "1")

        self.limit_entry.pack(pady=(0, 20))

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

        self.download_button.configure(
            state="disabled"
        )

        thread = threading.Thread(
            target=self.run_downloader,
            daemon=True
        )

        thread.start()

    def run_downloader(self):

        self.stdout.start()

        try:

            limit = int(self.limit_entry.get())

            run(

                workbook=self.excel_path.get(),

                limit=limit

            )

            print("\nDownload complete.")

        except Exception:

            print(traceback.format_exc())

        finally:

            self.stdout.stop()

            self.root.after(
                0,
                lambda: self.download_button.configure(
                    state="normal"
                )
            )

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

    def run(

            workbook=None,

            limit=0

        ):
        
        self.root.mainloop()