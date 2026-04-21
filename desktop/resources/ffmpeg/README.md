# FFmpeg for SRT2Web Desktop

Este directorio debe contener los binarios de FFmpeg para distribución.

## Cómo obtener FFmpeg

### Opción 1: Descargar estático
1. Ir a https://www.gyan.dev/ffmpeg/builds/
2. Descargar "ffmpeg-release-essentials.zip"
3. Extraer y copiar:
   - ffmpeg.exe → resources/ffmpeg/
   - ffprobe.exe → resources/ffmpeg/

### Opción 2: Usar chocolatey (Windows)
```powershell
choco install ffmpeg -y
# Luego copiar desde C:\ProgramData\chocolatey\bin\
```

### Opción 3: Compilar estático
```bash
# Linux/macOS
./configure --enable-static --disable-shared
make
# Copiar ffmpeg y ffprobe
```

## Nota

El launcher.py primero busca FFmpeg en:
1. `resources/ffmpeg/` (bundled)
2. PATH del sistema
3. Ubicaciones comunes de Windows

Si no encuentra ninguno, mostrará un warning pero continuará.
Los modelos se descargan al primer inicio si no existen.