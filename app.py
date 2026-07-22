from database.database import initialize_database

try:
    from ui.main_window import MainWindow
except ImportError:
    MainWindow = None


def main():
    print("=" * 60)
    print("Sera → ServiceTitan Migration Toolkit")
    print("=" * 60)

    initialize_database()

    if MainWindow is None:
        print("\nGUI has not been created yet.")
        print("Database initialized successfully.")
        print("Application startup successful.")
        return

    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()