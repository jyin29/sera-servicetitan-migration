import customtkinter as ctk


class MainWindow:

    def __init__(self):

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()

        self.root.title("Sera → ServiceTitan Migration")

        self.root.geometry("900x650")

        self.build()

    def build(self):

        title = ctk.CTkLabel(
            self.root,
            text="Sera → ServiceTitan Migration",
            font=("Segoe UI", 26, "bold")
        )

        title.pack(pady=30)

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

        self.log = ctk.CTkTextbox(
            self.root,
            width=760,
            height=350
        )

        self.log.pack(pady=25)

        self.write("Application started.\n")

    def write(self, text):
        self.log.insert("end", text)
        self.log.see("end")

    def download_clicked(self):
        self.write("Download button clicked.\n")

    def manifest_clicked(self):
        self.write("Generate Manifest clicked.\n")

    def upload_clicked(self):
        self.write("Upload button clicked.\n")

    def run(self):
        self.root.mainloop()