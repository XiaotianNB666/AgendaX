#define MyAppName "AgendaX"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "GCTech"
#define MyAppExeName "AgendaXLauncher.exe"
[Setup]
; --- 基本信息 ---
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; --- 安装行为 ---
DefaultDirName={code:GetInstallDir}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=AgendaX_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; --- 安装页配置 ---
; TasksPerPage=1

[Files]
; --- 主程序 ---
Source: "..\dist\AgendaXLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\AgendaX.exe"; DestDir: "{app}"; Flags: ignoreversion

; --- 资源 ---
Source: "..\resources\*"; DestDir: "{app}\resources"; Flags: recursesubdirs createallsubdirs

[Icons]
; --- 桌面快捷方式 ---
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; --- 开机自启 ---
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Tasks]
; 开机自启选项
Name: "startup"; Description: "Start AgendaX when Windows starts"; GroupDescription: "Additional tasks:";

[Run]
; --- 安装完成后启动 ---
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时清理残留
Type: filesandordirs; Name: "{app}"


; ============================================================
; 自定义安装路径逻辑
; ============================================================
[Code]
function GetInstallDir(Param: string): string;
begin
  Result := ExpandConstant('{localappdata}\{#MyAppName}');
end;