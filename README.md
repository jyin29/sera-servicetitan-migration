# Sera → ServiceTitan Migration Toolkit

A desktop application for migrating customer and job attachments from Sera into ServiceTitan.

## Features

- Downloads attachments from Sera
- Uploads attachments into ServiceTitan
- Job-level resume support
- Duplicate detection
- Progress tracking
- GUI interface
- Microsoft Edge automation via Playwright
- Automatic recovery after interruption

## Requirements

- Windows 10 or Windows 11
- Microsoft Edge
- Python 3.12+
- Playwright

## Installation

```bash
pip install -r requirements.txt
playwright install
```

## Running

```bash
python app.py
```

## Building

```bash
pyinstaller app.spec
```

or

```bash
build.bat
```

## Runtime Data

Application data is stored in

```
%LOCALAPPDATA%\Sera ServiceTitan Migration\
```

including

- browser profile
- migration logs
- resume files
- downloaded media

No runtime files are stored in the installation directory.

## Project Structure

```
ui/
sera/
servicetitan/
```

Main modules

- Migration Engine
- Downloader
- Inventory Builder
- Resume Tracker
- Migration Logger
- Browser Automation

## License

Private / Proprietary

Not licensed for redistribution.
