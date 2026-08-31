Set WshShell = CreateObject("WScript.Shell")

' Çalışma dizinini ayarla
Dim scriptDir
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
WshShell.CurrentDirectory = scriptDir

' Python sürecini başlat ve BİTMESİNİ BEKLE
WshShell.Run "py -3.11 ""manual_gui.py""", 0, True

' ---- Program kapandı (elle veya hata ile) --- Hepsini kapat ----
WshShell.Run "taskkill /F /IM brave.exe /T", 0, True
WshShell.Run "taskkill /F /IM chromedriver.exe /T", 0, True
WshShell.Run "taskkill /F /IM ffmpeg.exe /T", 0, True
WshShell.Run "taskkill /F /IM ffprobe.exe /T", 0, True
WshShell.Run "taskkill /F /IM yt-dlp.exe /T", 0, True
WshShell.Run "taskkill /F /IM python.exe /T", 0, True
WshShell.Run "taskkill /F /IM pythonw.exe /T", 0, True
WshShell.Run "taskkill /F /IM py.exe /T", 0, True
