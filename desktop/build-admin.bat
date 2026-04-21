@echo off
echo Building SRT2Web NSIS installer...
cd /d C:\Users\bruno\Documents\programacion\Antigravity\srt2web\desktop
powershell -Command Start-Process -FilePath cmd -ArgumentList '/c cd /d C:\Users\bruno\Documents\programacion\Antigravity\srt2web\desktop ^&^& electron-builder --win nsis' -Verb RunAs