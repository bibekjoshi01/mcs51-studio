; Values are supplied by scripts/build_release.py.
[Setup]
AppId={{7F26DAAE-A325-4C16-AC1A-4F3D40F5BF8B}
AppName=MCS51 Studio
AppVersion={#AppVersion}
AppPublisher=MCS51 Studio
SetupIconFile={#IconFile}
LicenseFile={#LicenseFile}
DefaultDirName={localappdata}\Programs\MCS51 Studio
DefaultGroupName=MCS51 Studio
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
UninstallDisplayIcon={app}\MCS51 Studio.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MCS51 Studio"; Filename: "{app}\MCS51 Studio.exe"; AppUserModelID: "{#AppUserModelID}"

[Run]
Filename: "{app}\MCS51 Studio.exe"; Description: "Launch MCS51 Studio"; Flags: nowait postinstall skipifsilent
