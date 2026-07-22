Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\tooltaoanh"
WshShell.Run "pythonw main_app.py", 0, False
