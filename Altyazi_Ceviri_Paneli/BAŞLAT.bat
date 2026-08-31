@echo off
chcp 65001 >nul
title Altyazı Çeviri Paneli Başlatıcı
cd /d "%~dp0Sadece Çeviri"
start "" wscript.exe "baslat_gizli.vbs"
exit
