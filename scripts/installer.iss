[Setup]
AppId={{2C46E8B2-97AB-48E1-B5A4-9A76D32B3B05}
AppName=Elisei Finanças
AppPublisher=Eliseu Souza dos Santos
AppVersion=0.3.0
DefaultDirName={localappdata}\Programs\Horizonte
DefaultGroupName=Elisei
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.18362
OutputDir=..\release
OutputBaseFilename=Elisei-Instalar-0.3.0-Windows-x64
SetupIconFile=..\src\elisei.ico
UninstallDisplayIcon={app}\Elisei.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
CreateUninstallRegKey=not IsTestMode
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Files]
Source: "..\dist\Elisei\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"
[InstallDelete]
Type: files; Name: "{app}\Horizonte.exe"
Type: files; Name: "{userprograms}\Horizonte\Horizonte.lnk"; Check: not IsTestMode
[Icons]
Name: "{group}\Elisei"; Filename: "{app}\Elisei.exe"; Check: not IsTestMode
Name: "{userdesktop}\Elisei"; Filename: "{app}\Elisei.exe"; Tasks: desktopicon; Check: not IsTestMode
[Run]
Filename: "{app}\Elisei.exe"; Description: "Abrir Elisei"; Flags: nowait postinstall skipifsilent; Check: not IsTestMode

[Code]
function IsTestMode: Boolean;
begin
  Result := ExpandConstant('{param:TESTMODE|0}') = '1';
end;
  
