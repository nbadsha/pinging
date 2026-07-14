Build instructions for creating a Windows executable from `ping4.py`.

Prerequisites:
- Windows machine with Python installed (Anaconda in this workspace).
- Developer tools and permissions to install packages.

Quick build (from PowerShell):

```powershell
cd C:\Users\Administrator\Downloads
& C:/Users/Administrator/anaconda3/python.exe -m pip install --upgrade pip setuptools wheel
& C:/Users/Administrator/anaconda3/python.exe -m pip install -r requirements.txt
& C:/Users/Administrator/anaconda3/python.exe -m PyInstaller --noconfirm --onefile --windowed --name Ping4 ping4.py
```

After successful build, the EXE will be in `dist\Ping4.exe`.

Notes:
- The `--windowed` flag hides the console; remove it to keep the console visible.
- If the build fails due to missing Tcl/Tk data files, ensure your Python installation includes Tkinter (Anaconda typically does) and rerun.
- If you want an installer (MSI/NSIS), use third-party packagers on the produced exe.
