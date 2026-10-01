import os
import sys
from pathlib import Path
import win32com.client

desktop = Path(os.environ['USERPROFILE']) / 'Desktop'
lnk_path = desktop / '启动小红书剪贴板采集.lnk'

pythonw = Path(sys.executable).parent / 'pythonw.exe'
script = Path(r'D:\AICode\工具开发\projects\xhs-dl\clipboard_xhs_auto_collector.py')

shell = win32com.client.Dispatch('WScript.Shell')
sc = shell.CreateShortcut(str(lnk_path))
sc.TargetPath = str(pythonw)
sc.Arguments = f'"{script}"'
sc.WorkingDirectory = str(script.parent)
sc.Description = '小红书剪贴板无感智能采集守护程序（随手复制即入库）'

icon = Path(r'D:\AICode\工具开发\projects\XHS_Downloader\static\XHS-Downloader.ico')
if icon.exists():
    sc.IconLocation = f'{icon},0'

sc.Save()
print(f'[OK] Shortcut created successfully at: {lnk_path}')
