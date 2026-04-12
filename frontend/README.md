# SRT2Web - Frontend

Interfaz web para streaming de video en tiempo real con subtítulos traducidos.

## Estructura

```
frontend/
├── src/
│   ├── components/       # Componentes UI
│   │   ├── layout/      # Header, Footer
│   │   └── ui/          # Button, Input, Toggle, Badge, Card
│   ├── lib/             # Módulos JavaScript
│   │   ├── api.ts       # API client
│   │   ├── dashboard.ts # Dashboard principal
│   │   ├── modules/    # Módulos por área
│   │   │   ├── events.ts
│   │   │   ├── player.ts
│   │   │   ├── ui.ts
│   │   │   └── config.ts
│   │   └── utils/       # Utilidades
│   ├── pages/           # Páginas Astro
│   │   ├── index.astro  # Dashboard
│   │   └── player.astro # Reproductor HLS
│   └── styles/         # Estilos CSS
├── public/              # Assets estáticos
├── tailwind.config.js   # Configuración Tailwind
└── astro.config.mjs    # Configuración Astro
```

## Tecnologías

- **Astro** 6.x - Framework web
- **Tailwind CSS** 4.x - Estilos
- **TypeScript** - Tipos

## Comandos

```bash
cd frontend
npm install
npm run dev      # Desarrollo localhost:4321
npm run build    # Build a server/static
```

## Módulos JavaScript

### api.ts
```typescript
getAuthToken()    // Obtener token
setAuthToken()     // Guardar token
clearAuthToken()   // Limpiar token
getWebSocketUrl()  // WebSocket URL con auth
apiCall()          // Llamadas API
getConfig()        // Obtener config
startPipeline()    // Iniciar pipeline
stopPipeline()     // Detener pipeline
```

### dashboard.ts
```typescript
initDashboard()              // Inicializar dashboard
initWebSocket()           // Conectar WebSocket
handleInputTypeChange()    // Cambio tipo input
handleOutputFormatChange() // Cambio formato output
```

---

## Estado del Proyecto (2026-04-12)

**Versión**: 0.6.5  
**Tests**: 527 passing ✅

### Módulos del Pipeline

1. **SRTInput** - Entrada SRT (puerto 9000)
2. **AudioExtractor** - Extrae audio del video
3. **Transcriber** - Whisper (tiny~large)
4. **Translator** - Argos Translate
5. **TTSEngine** - Piper TTS
6. **AudioMixer** - Mezcla audio original + TTS
7. **VideoMuxer** - Salida HLS (WebRTC opcional)
8. **SubtitleGenerator** - VTT subtitles

### Configuración Low-Latency

```yaml
pipeline:
  chunk_duration_sec: 10
output:
  web:
    segment_duration: 10
    list_size: 2
```

### Características

- ✅ Recover automático SRT (FFmpegWatchdog)
- ✅ Pool de procesos FFmpeg
- ✅ GPU acceleration (NVENC, QSV, AMF)
- ✅ WebSocket en tiempo real
- ✅ Subtítulos traduzidos en vivo
- ✅ 527 tests passing