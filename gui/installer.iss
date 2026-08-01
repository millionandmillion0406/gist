#define MyAppName "Link Distill"
#define MyAppVersion "2.1.1"
#define MyAppPublisher "Link Distill"
#define MyAppExeName "LinkDistill.exe"

[Setup]
AppId={{8A71EE58-EFC0-41AF-B999-2BF91233D480}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Link Distill
DefaultGroupName=Link Distill
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
OutputDir=release
OutputBaseFilename=LinkDistill-Setup-{#MyAppVersion}-x64
Compression=zip
SolidCompression=no
WizardStyle=modern
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "dist\LinkDistill\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Link Distill"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Link Distill"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "正在检查 WebView2 Runtime..."; Flags: waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "启动 Link Distill"; Flags: nowait postinstall skipifsilent
