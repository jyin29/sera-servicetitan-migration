def upload_to_customer(self, files):

    print("Locating customer upload input...")

    upload = self.page.locator(
        '[data-tracking-id="crm-customer-add-attachment-button"] + input[type=file]'
    )

    print("Matching inputs:", upload.count())

    return self._upload_files(upload, files)