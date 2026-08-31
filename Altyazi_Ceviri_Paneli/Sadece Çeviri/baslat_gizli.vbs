Set WshShell = CreateObject("WScript.Shell")

' VBS dosyasinin bulundugu klasoru dinamik olarak al (Turkce karakter sorunu yok)
Dim scriptDir
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)

WshShell.CurrentDirectory = scriptDir

' 0 = pencere gizli, False = beklemeden devam et
WshShell.Run "python ng_app.py", 0, False
