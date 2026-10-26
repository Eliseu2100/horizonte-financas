[Setup]
AppId={{2C46E8B2-97AB-48E1-B5A4-9A76D32B3B05}
AppName=Horizonte
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\Horizonte
DefaultGroupName=Horizonte
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.18362
OutputDir=..\release
OutputBaseFilename=Horizonte-Instalar-0.1.0-Windows-x64
SetupIconFile=..\src\horizonte.ico
UninstallDisplayIcon={app}\Horizonte.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Files]
Source: "..\dist\Horizonte\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\Horizonte"; Filename: "{app}\Horizonte.exe"
[Run]
Filename: "{app}\Horizonte.exe"; Description: "Abrir Horizonte"; Flags: nowait postinstall skipifsilent
