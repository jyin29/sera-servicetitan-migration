#define MyAppName "Sera ServiceTitan Migration"
#define MyAppVersion "1.4"
#define MyAppPublisher "JYStudios"
#define MyAppExeName "Sera ServiceTitan Migration.exe"

[Setup]
AppId={{F58D4D80-4D64-4F1A-90F3-001337001337}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=Sera_ServiceTitan_Migration_Setup_v1.4
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

SetupIconFile=..\assets\Sera_ServiceTitan_Icon_Dark.ico
WizardImageFile=..\assets\installer.bmp
;WizardSmallImageFile=..\assets\Sera_ServiceTitan_Icon_Dark.bmp

UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\Sera ServiceTitan Migration.exe"; DestDir: "{app}"; Flags: ignoreversion

Source: "..\assets\Sera_ServiceTitan_Icon_Dark.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Sera ServiceTitan Migration"; Flags: nowait postinstall skipifsilent