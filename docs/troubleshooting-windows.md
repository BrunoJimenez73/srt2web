# Troubleshooting Windows

> Common issues and solutions for running SRT2Web on Windows 10/11.
> Counterpart of `docs/troubleshooting-mac.md`.

## Installation Issues

### `python` not found

```
'python' is not recognized as an internal or external command
```

**Causa**: Python no instalado, o no está en el PATH.

**Solución**:
1. Descarga Python 3.12 desde https://www.python.org/downloads/
2. **Marca "Add Python to PATH"** en el primer diálogo del instalador
3. Reabre la terminal después de instalar
4. Verifica: `python --version` debe responder `Python 3.12.x`

### `venv\Scripts\python.exe` no encontrado después de `Install.bat`

**Causa**: el venv no se creó. Casi siempre porque `python` (sin marcar PATH) no resolvió correctamente.

**Solución**: ver `python` not found arriba.

### `pip install` falla con `Access Denied`

```
ERROR: Could not install packages due to an OSError: [WinError 5] Access is denied
```

**Causa**: otra terminal tiene archivos del venv abiertos (servidor corriendo, o pytest tmp dirs zombies).

**Solución**:
1. Cierra todas las terminales donde puedas tener el venv activado
2. Si tienes un server srt2web corriendo: `.\Stop.bat`
3. Si el error persiste: borra `venv\` y re-ejecuta `Install.bat`

### `pip install torch` falla con `Microsoft Visual C++ 14.0 required`

**Causa**: PyTorch necesita MSVC build tools en algunos casos. Raro en 2026 con wheels precompilados, pero puede pasar con Python 3.13.

**Solución**: usar Python 3.12 (recomendado oficialmente), que tiene wheels precompilados para Windows.

---

## Runtime Issues

### 🔴 `ImportError: DLL load failed while importing _multiarray_umath: Una directiva de Control de aplicaciones bloqueó este archivo.`

**Síntoma**: el server no arranca. El log (`logs/srt2web_error.log` o stderr) contiene:

```
ImportError: DLL load failed while importing _multiarray_umath: Una directiva de Control de aplicaciones bloqueó este archivo.
```

seguido de:

```
Importing the numpy C-extensions failed. This error can happen for
many reasons, often due to issues with your setup or how NumPy was
installed.
```

y referencia a `numpy 2.4.x` o superior.

**Causa**: numpy 2.4+ carga una extensión C (`_multiarray_umath.pyd`) que está siendo bloqueada por una política de seguridad de Windows. Las tres causas más comunes son:

1. **Windows Defender SmartScreen / Controlled Folder Access** — la DLL `.pyd` no tiene firma reconocida y es bloqueada.
2. **AppLocker corporativo** — la política de la empresa bloquea DLLs no aprobadas de `venv\Lib\site-packages\`.
3. **Antivirus / EDR (CrowdStrike, SentinelOne, Defender for Endpoint)** — heurística marca la DLL como sospechosa.

**Diagnóstico**:

```powershell
# ¿Qué versión de numpy está intentando cargar?
python -c "import numpy; print(numpy.__version__)"

# ¿La DLL física está en disco?
dir venv\Lib\site-packages\numpy\_core\_multiarray_umath.cp312-win_amd64.pyd

# ¿El proceso python tiene permiso de lectura?
icacls venv\Lib\site-packages\numpy\_core\_multiarray_umath.cp312-win_amd64.pyd
```

**Soluciones (en orden de menos a más invasivo)**:

#### Solución 1: Reinstalar numpy desde el binario oficial

```powershell
cd C:\path\to\srt2web
.\Stop.bat
venv\Scripts\python.exe -m pip uninstall numpy -y
venv\Scripts\python.exe -m pip install numpy==2.4.5 --only-binary=:all:
```

Si la nueva versión se carga OK, el problema era de la versión anterior. Si falla con la misma DLL, pasa a la Solución 2.

#### Solución 2: Añadir el venv a la exclusión de SmartScreen / Controlled Folder Access

1. **Windows Security** → **Virus & threat protection** → **Manage settings** (bajo "Virus & threat protection settings")
2. Scroll hasta **Exclusions** → **Add or remove exclusions**
3. Añade la carpeta: `C:\path\to\srt2web\venv\` (tipo "Folder")
4. Reinicia la terminal y reintenta: `python -c "import numpy"`

#### Solución 3: Desbloquear la DLL específica

PowerShell con permisos de admin:

```powershell
# Desbloquear TODOS los .pyd del venv
Get-ChildItem -Path "C:\path\to\srt2web\venv\Lib\site-packages" -Recurse -Filter "*.pyd" | Unblock-File
```

#### Solución 4: Mover el venv fuera de la zona controlada

Algunos EDR son muy agresivos con la carpeta del proyecto si está en OneDrive, Documents, o Desktop. Mueve el proyecto a una ruta sin sincronización:

```powershell
# Antes: C:\Users\<user>\Documents\programacion\Antigravity\srt2web
# Después: C:\apps\srt2web  (raíz del disco, sin sync)
```

#### Solución 5: Hablar con IT (entornos corporativos)

Si estás en un equipo con política de AppLocker o EDR administrado:

1. Reporta el path exacto: `C:\path\to\srt2web\venv\Lib\site-packages\numpy\_core\_multiarray_umath.cp312-win_amd64.pyd`
2. Pide al equipo de seguridad que añada una exclusión para esta DLL
3. Como workaround temporal, usa un Python portable en una carpeta que ya esté excluida (ej. `C:\Python312\`)

#### Solución 6: Downgrade a numpy 1.x (último recurso)

numpy 1.x no usa las nuevas C extensions y a veces esquiva la política. Solo si las soluciones 1-5 no funcionan:

```powershell
venv\Scripts\python.exe -m pip install "numpy<2" --force-reinstall
```

⚠️ **No recomendado** — algunas features recientes (F108 HLS native subs, etc.) pueden romperse con numpy 1.x.

---

### `OSError: [WinError 1314] A required privilege is not held by the client`

**Causa**: el proceso está intentando usar un puerto < 1024 sin permisos de admin. srt2web usa puertos altos (9999, 9000, 1935) por defecto, pero si configuras algo exótico, puede pasar.

**Solución**: cambia el puerto en `config.yaml` a uno > 1024, o ejecuta la terminal como admin.

### Server arranca pero no se ve en `http://localhost:9999`

**Causa**: firewall de Windows bloqueando Python.

**Solución**:
1. **Windows Security** → **Firewall & network protection** → **Allow an app through firewall**
2. Click **Change settings** → **Allow another app...**
3. Busca `C:\path\to\srt2web\venv\Scripts\python.exe` y añádelo
4. Marca las casillas **Private** y **Public**

### Player HLS no carga, queda en "Loading..." eterno

**Causa**: el browser bloquea HLS.js o el manifest no se genera.

**Diagnóstico**:
1. Abre `http://localhost:9999/player` en el browser
2. DevTools (F12) → Console → busca errores
3. DevTools → Network → verifica que `master.m3u8` (o `subs.m3u8` si solo subs) responde 200

**Solución común**: el antivirus bloquea el localhost. Añade `http://localhost:9999` a exclusiones del proxy/firewall.

### `UnicodeDecodeError: 'charmap' codec can't decode` al leer `config.yaml`

**Causa**: Windows abre archivos en modo cp1252 por defecto. Si el YAML tiene caracteres UTF-8, falla.

**Solución**: ya está manejado en `core/config_manager.py` con `encoding="utf-8"`. Si lo ves, es bug — repórtalo con el archivo y la traza completa.

### `OSError: [Errno 28] No space left on device`

**Causa**: el disco está lleno, casi siempre por `output/hls/` o `output/recordings/` que crecen sin rotación.

**Solución**:
1. Borra `output/recordings/*.mp4` antiguos desde la UI (botón papelera)
2. Si `output/hls/` está lleno: `Remove-Item output\hls\*.ts -Recurse -Force`
3. Configura rotación automática (F114 si no está done)

---

## Performance Issues

### Latencia > 30s incluso con `low_latency` preset

**Diagnóstico**:
```powershell
# Mira los logs del pipeline
type logs\srt2web.log | Select-String "chunk" | Select-Object -Last 20
```

**Causas comunes**:
- Whisper con modelo `large-v2/v3` en CPU → 8-15s por chunk. Usa `medium` o `tiny` para baja latencia.
- Piper TTS no usa GPU → 2-5s extra por chunk. Verifica con `nvidia-smi`.
- SRT latency_ms muy alto (> 500ms) en `config.yaml`.

### GPU badge dice "CPU" aunque tienes NVIDIA

**Causa**: CUDA no está en PATH, o PyTorch no se instaló con CUDA.

**Solución**:
```powershell
# Verificar CUDA
nvidia-smi

# Verificar PyTorch
venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
# Debe responder True

# Si es False: reinstalar con CUDA
venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall
```

---

## Getting Help

Si ninguna de las soluciones anteriores funciona:

1. Recoge un diagnóstico completo:
   ```powershell
   venv\Scripts\python.exe --version
   venv\Scripts\python.exe -c "import numpy, torch, faster_whisper, onnxruntime; print('all ok')"
   venv\Scripts\python.exe -m pip list > installed_packages.txt
   ```
2. Copia los últimos 50 líneas de `logs/srt2web_error.log`
3. Abre un issue en https://github.com/BrunoJimenez73/srt2web/issues con:
   - Salida del diagnóstico
   - Log de error
   - Versión de Windows (Settings → About)
   - Si aplica: confirmación de que el equipo tiene política corporativa (AppLocker/EDR)

Para issues internos del proyecto, ver también `docs/troubleshooting-mac.md` (algunos problemas son cross-platform).
