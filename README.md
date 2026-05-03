# SRT2Web

## Instalación rápida

```bash
# Clonar el repositorio
git clone https://github.com/BrunoJimenez73/srt2web.git
cd srt2web

# Crear entorno virtual (Python 3.12)
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate   # macOS/Linux

# Instalar dependencias
pip install -r requirements.txt

# Instalar dependencias del frontend
cd frontend
npm install
cd ..

# Compilar frontend (producción)
npm run build:local   # o: cd frontend && npm run build:local

# Ejecutar servidor
.\Start.bat   # Windows
# o en Linux/macOS:
python -m venv venv && source venv/bin/activate && python main.py
```

## Uso

- Accede a la UI en `http://localhost:9999/`.
- La API está disponible bajo `/api`.
- HLS stream disponible en `/hls`.

## Desarrollo

- Ejecuta los tests: `python -m pytest tests/unit -v`.
- Linter y formateo: `ruff .` y `prettier