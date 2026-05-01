# Arquitectura - SRT2Web

## Diagrama General del Sistema

```mermaid
graph TB
    subgraph Source["Fuentes de Entrada"]
        OBS[OBS Studio SRT]
        RTMP_SRC[Servidor RTMP]
        FILE[Archivo Video]
    end

    subgraph Server["SRT2Web Server"]
        subgraph Inputs["Input Modules"]
            I_SRT[SRT Input]
            I_RTMP[RTMP Input]
            I_FILE[File Input]
        end
        subgraph Pipeline["Pipeline Core"]
            AE[Audio Extractor]
            TR[Transcriber Whisper]
            TL[Translator Argos]
            SG[Subtitle Generator]
            TTS[TTS Engine Piper]
            MX[Audio Mixer numpy]
            VM[Video Muxer HLS/WebRTC]
        end
        subgraph Outputs["Output System"]
            CO[Composite Output]
            H[HLSOutput]
            R[RTMPOutput]
            S[SRTOutput]
            W[WebRTCOutput]
            REC[RecordingOutput]
            F[FileOutput]
        end
        WS[WebSocket Logs]
        API[REST API]
    end

    subgraph ML["Machine Learning"]
        WHISPER[Whisper OpenAI]
        ARGOS[Argos Translate]
        PIPER[Piper TTS Subprocess]
    end

    subgraph Frontend["Frontend"]
        UI[Dashboard Astro+Signals]
        PLAYER[HLS Player video.js]
        WEBRTC[WebRTC Player]
    end

    subgraph Output["Destinos"]
        HLS[HLS .m3u8+.ts]
        RTMP_DST[Servidor RTMP]
        SRT_DST[Destino SRT]
        WEBRTC_DST[Browser WebRTC]
        REC_FILE[Grabación .mp4]
    end

    OBS --> I_SRT
    RTMP_SRC --> I_RTMP
    FILE --> I_FILE

    I_SRT --> AE
    I_RTMP --> AE
    I_FILE --> AE

    AE --> TR
    TR --> TL
    TL --> SG
    SG --> TTS
    TTS --> MX
    MX --> VM
    VM --> CO

    CO --> H
    CO --> R
    CO --> S
    CO --> W
    CO --> REC
    CO --> F

    TR --> WHISPER
    TL --> ARGOS
    TTS --> PIPER

    H --> HLS
    R --> RTMP_DST
    S --> SRT_DST
    W --> WEBRTC_DST
    REC --> REC_FILE

    Server -.-> WS
    HLS --> PLAYER
    WEBRTC_DST --> WEBRTC
    Server --> UI

    style Source fill:#e1f5fe
    style ML fill:#fff3e0
    style Output fill:#e8f5e9
    style Frontend fill:#f3e5f5
```

## Pipeline de Procesamiento

```mermaid
sequenceDiagram
    participant SRC as Input (SRT/RTMP/File)
    participant AE as Audio Extractor
    participant TR as Transcriber
    participant TL as Translator
    participant SG as Subtitle Gen
    participant TTS as TTS Engine
    participant MX as Audio Mixer
    participant VM as Video Muxer
    participant CO as Composite Output

    SRC->>AE: video_chunk_path (cada 10s)
    AE->>AE: Extract audio track
    AE->>TR: audio_chunk_path

    TR->>TR: Whisper transcription
    TR-->>TL: transcribed text

    TL->>TL: Argos translate
    TL-->>SG: translated text + segments

    SG->>SG: Generate VTT (rolling window)
    SG-->>TTS: subtitle text for synthesis

    TTS->>TTS: Piper TTS (subprocess)
    TTS-->>MX: tts_audio.wav

    MX->>MX: numpy mix (original ducked + TTS)
    MX-->>VM: mixed_audio.wav

    VM->>VM: FFmpeg mux A/V → HLS segments
    VM->>CO: video segments

    CO->>CO: Distribute to all active outputs
    CO->>HLS: .m3u8 + .ts segments
    CO->>RTMP: RTMP push
    CO->>REC: Continuous recording
```

## Arquitectura de Módulos

```mermaid
classDiagram
    class ModuleBase {
        <<abstract>>
        +name: str
        +enabled: bool
        +state: ModuleState
        +processed_chunks: int
        +initialize(config: dict) None
        +process(data: PipelineData) PipelineData
        +get_status() dict
        +shutdown() None
    }

    class InputSource {
        <<interface>>
        +connect() bool
        +disconnect() None
        +read_chunk() Optional[Chunk]
        +get_connection_info() dict
    }

    class OutputSink {
        <<interface>>
        +write(data: Any) bool
        +flush() None
        +close() None
        +get_status() dict
    }

    class SRTInput {
        +port: int
        +mode: listener|caller
        +latency_ms: int
    }

    class RTMPInput {
        +port: int
        +app: str
        +stream_key: str
    }

    class FileInput {
        +path: str
        +loop: bool
        +speed: float
    }

    class HLSOutput {
        +segment_duration: int
        +list_size: int
        +encoder_mode: str
    }

    class RecordingOutput {
        +output_path: str
        +split_mode: none|time|size
        +subtitles: none|burnt|track|vtt
        +codec: copy|h264_nvenc|libx264
    }

    class WebRTCOutput {
        +server: MediaMTX
        +path: str
        +video_codec: h264|vp8|av1
        +audio_codec: opus
    }

    class CompositeOutput {
        +outputs: dict[str, OutputSink]
        +add_output(name, type, config)
        +remove_output(name)
        +toggle_output(name, enabled)
    }

    ModuleBase <|-- SRTInput
    ModuleBase <|-- RTMPInput
    ModuleBase <|-- FileInput
    ModuleBase <|-- HLSOutput
    ModuleBase <|-- RecordingOutput
    ModuleBase <|-- WebRTCOutput

    InputSource <|-- SRTInput
    InputSource <|-- RTMPInput
    InputSource <|-- FileInput

    OutputSink <|-- HLSOutput
    OutputSink <|-- RecordingOutput
    OutputSink <|-- WebRTCOutput

    CompositeOutput --> OutputSink : manages
```

## Sistema Multi-Output

```mermaid
graph LR
    VM[Video Muxer] --> CO[Composite Output]
    CO --> H[HLS web_1]
    CO --> R[RTMP rtmp_1]
    CO --> REC[Recording grab_1]
    CO --> W[WebRTC webrtc_1]

    classDef active fill:#4caf50,color:#fff
    classDef inactive fill:#9e9e9e,color:#fff

    class H active
    class R inactive
    class REC active
    class W inactive
```

El sistema de **salidas múltiples** permite distribuir el mismo stream a varios destinos simultáneamente:

| Output Type | Alias                     | Config Key         | Descripción                  |
| ----------- | ------------------------- | ------------------ | ---------------------------- |
| HLS         | `web`, `webplayer`, `hls` | `output.web`       | Streaming para navegador     |
| RTMP        | `rtmp`                    | `output.rtmp`      | Push a servidor RTMP externo |
| SRT         | `srt`                     | `output.srt`       | Output via protocolo SRT     |
| WebRTC      | `webrtc`                  | `output.webrtc`    | Streaming baja latencia      |
| Recording   | `recording`               | `output.recording` | Grabación continua a archivo |
| File        | `file`                    | `output.file`      | Guardar chunks como archivos |

**Configuración** en `config.yaml`:

```yaml
# Salida principal
output:
  type: web
  web:
    segment_duration: 4
    list_size: 6

# Salidas adicionales simultáneas
outputs:
  - name: recording_1
    type: recording
    enabled: true
    config:
      output_path: ./output/grabacion.mp4
      codec: copy
      subtitles: track # Subtítulos como pista separada
  - name: rtmp_1
    type: rtmp
    enabled: false
    config:
      url: rtmp://youtube.com/live/xxx
```

## Flujo de Datos

```mermaid
flowchart LR
    subgraph Input["Entrada"]
        SRT[SRT Stream]
        RTMP[RTMP Stream]
        FILE[Archivo Local]
    end

    subgraph Buffer["Buffer de Chunks"]
        B1[Chunk 1 10s]
        B2[Chunk 2 10s]
        B3[Chunk 3 10s]
    end

    subgraph Process["Procesamiento Paralelo"]
        subgraph Audio
            A1[Audio Extract]
            T1[Transcribe]
            L1[Translate]
            S1[Subtitles VTT]
            P1[TTS Synthesis]
            M1[numpy Mix]
        end
        subgraph Video
            V1[HLS Segments]
        end
    end

    subgraph Output["Salidas Múltiples"]
        HLS[HLS Stream]
        RTMP_OUT[RTMP Push]
        SRT_OUT[SRT Output]
        WEBRTC_OUT[WebRTC]
        REC[Grabación]
    end

    subgraph UI["Frontend"]
        DASH[Dashboard]
        WSS[WebSocket]
    end

    SRT --> B1
    RTMP --> B2
    FILE --> B3

    B1 --> A1
    B1 --> V1

    A1 --> T1 --> L1 --> S1 --> P1 --> M1

    V1 --> HLS
    M1 --> HLS
    HLS --> RTMP_OUT
    HLS --> SRT_OUT
    HLS --> WEBRTC_OUT
    HLS --> REC

    B1 -.-> WSS
    HLS -.-> DASH

    style Input fill:#e3f2fd
    style Buffer fill:#fff8e1
    style Process fill:#f3e5f5
    style Output fill:#e8f5e9
    style UI fill:#fff3e0
```

## Arquitectura de Seguridad

```mermaid
flowchart TB
    subgraph Client["Clientes"]
        UI[Browser Dashboard]
        OBS[OBS Studio SRT]
        CLI[CLI Tool]
    end

    subgraph Security["Middleware Stack"]
        RH[Rate Limiter configurable]
        AH[Auth Token Headers]
        SH[Security Headers CORS/CSP]
        RL[Request Size Limit 100MB]
    end

    subgraph Server["API"]
        WS[WebSocket Auth Token]
        API[REST API Token]
    end

    subgraph Backend["Backend"]
        P[Pipeline]
        M[Modules]
        FS[File System]
    end

    UI --> RH
    CLI --> RH
    OBS --> RH

    RH --> AH --> SH --> RL

    RL --> WS
    RL --> API

    WS --> P
    API --> P
    P --> M --> FS

    style Security fill:#ffebee
```

## Estado de Módulos

```mermaid
stateDiagram-v2
    [*] --> Idle

    state Idle {
        [*] --> Disabled
        Disabled --> Enabled: enable()
        Enabled --> Disabled: disable()
    }

    state Processing {
        [*] --> Initializing
        Initializing --> Ready: init complete
        Ready --> Running: process start
        Running --> Ready: chunk complete
        Running --> Error: exception
        Error --> Ready: retry
    }

    Idle --> Processing: start_pipeline()
    Processing --> Idle: stop_pipeline()

    state Error {
        [*] --> Recoverable
        Recoverable --> Ready: recovery
        Recoverable --> Fatal: max retries
        Fatal --> [*]: shutdown
    }
```

## Frontend: Signals & Effects

```mermaid
graph LR
    subgraph Store["State Management"]
        S[pipelineStatus signal]
        C[pipelineConfig signal]
        L[pipelineLogs signal]
        W[wsConnected signal]
    end

    subgraph Computed["Computed Values"]
        CS[pipelineState]
        IR[isPipelineRunning]
        SM[systemMetrics]
    end

    subgraph Effects["DOM Effects"]
        E1[Pipeline Indicator]
        E2[Metrics Display]
        E3[Module Status]
        E4[Connection URLs]
        E5[Clock]
    end

    S --> CS
    S --> IR
    C --> SM
    W --> E4

    CS --> E1
    SM --> E2
    S --> E3
    E4 --> E4
```

El frontend usa **Preact Signals** para gestión de estado reactivo:

- **Signals** (`store/signals.ts`): State atoms (`pipelineStatus`, `pipelineConfig`, `pipelineLogs`, `wsConnected`)
- **Computed** (`store/signals.ts`): Derived values (`pipelineState`, `isPipelineRunning`, `systemMetrics`, `connectionUrls`)
- **Effects** (`store/effects.ts`): DOM updates automáticos cuando signals cambian
- **API** (`api.ts`): HTTP calls con auth token, WebSocket management

## Pipeline Modes

| Mode              | Clase                    | Descripción                                  |
| ----------------- | ------------------------ | -------------------------------------------- |
| `sequential`      | `SequentialPipeline`     | Procesamiento chunk a chunk (menor latencia) |
| `thread_parallel` | `ThreadParallelPipeline` | Módulos en paralelo con ThreadPoolExecutor   |
| `async`           | `AsyncPipeline`          | Pipeline completamente asíncrono             |

```yaml
pipeline:
  mode: thread_parallel # sequential | thread_parallel | async
  max_concurrent_chunks: 4 # Chunks procesados simultáneamente
  chunk_duration_sec: 15 # Duración de cada chunk
  buffer_size: 2 # Buffer de chunks en memoria
```

## Dependencias del Sistema

```mermaid
graph BT
    subgraph Python["Python 3.12"]
        FA[FastAPI]
        PT[PyTorch]
        OR[ONNX Runtime]
        PNL[pynvml]
    end

    subgraph ML["Machine Learning"]
        WH[Whisper]
        AG[Argos Translate]
        PP[Piper TTS]
    end

    subgraph Video["Video/Audio"]
        FF[FFmpeg]
        NV[NVIDIA CUDA]
        MMTX[MediaMTX WebRTC]
    end

    subgraph Front["Frontend"]
        AS[Astro]
        TW[Tailwind CSS]
        VJ[video.js]
        SG[Preact Signals]
        VT[Vitest]
    end

    subgraph Tools["Herramientas"]
        CLI[CLI Tool]
        ELEC[Electron Desktop]
    end

    FA --> PT --> NV
    PT --> OR

    WH --> PT
    AG --> OR
    PP --> OR

    AS --> TW
    AS --> VJ
    AS --> SG

    style Python fill:#e1f5fe
    style ML fill:#fff3e0
    style Video fill:#e8f5e9
    style Front fill:#f3e5f5
    style Tools fill:#fce4ec
```

## Estructura de Directorios

```
srt2web/
├── core/                    # Núcleo del sistema
│   ├── pipeline/            # Pipeline modes
│   │   ├── sequential.py    # Procesamiento secuencial
│   │   ├── parallel.py      # ThreadPoolExecutor
│   │   ├── async_pipeline.py # Async pipeline
│   │   ├── factory.py       # Pipeline factory
│   │   └── base.py          # Base classes
│   ├── pipeline.py          # Pipeline orchestrator
│   ├── pipeline_manager.py  # Gestión de lifecycle
│   ├── config_manager.py    # Configuración con hot-reload
│   ├── config_schema.py     # Validación de schemas
│   ├── module_base.py       # Clase base módulos
│   ├── module_interface.py  # ProcessingModule Protocol
│   ├── io_factory.py        # Factory inputs/outputs
│   ├── input_source.py      # InputSource interface
│   ├── output_sink.py       # OutputSink interface
│   ├── ffmpeg_pool.py       # Pool procesos FFmpeg
│   ├── ffmpeg_utils.py      # Utilidades FFmpeg
│   ├── model_cache.py       # Cache modelos ML
│   ├── hardware_monitor.py  # Monitor GPU/CPU/RAM
│   ├── mediarmtx_manager.py # Gestión MediaMTX WebRTC
│   ├── encoder_config.py    # Configuración encoders
│   ├── network_utils.py     # Utilidades red
│   ├── watchdog.py          # Watchdog de procesos
│   ├── security.py          # Middleware seguridad
│   ├── logging_setup.py     # Logging con file rotation
│   ├── cuda_paths.py        # CUDA path config
│   ├── constants.py         # Constantes globales
│   ├── types.py             # Tipos compartidos
│   ├── exceptions.py        # Excepciones custom
│   └── paths.py             # Path utilities
│
├── modules/                 # Módulos de procesamiento
│   ├── inputs/              # Fuentes de entrada
│   │   ├── base.py          # InputSource base
│   │   ├── srt_input.py     # SRT protocol
│   │   ├── rtmp_input.py    # RTMP protocol
│   │   └── file_input.py    # Video file input
│   ├── outputs/             # Salidas múltiples
│   │   ├── base.py          # OutputSink base
│   │   ├── hls_output.py    # HLS streaming
│   │   ├── rtmp_output.py   # RTMP push
│   │   ├── srt_output.py    # SRT output
│   │   ├── webrtc_output.py # WebRTC streaming
│   │   ├── recording_output.py # Grabación continua
│   │   ├── file_output.py   # File chunk output
│   │   └── composite_output.py # Multi-output manager
│   ├── transcriber.py       # Whisper transcription
│   ├── translator.py        # Argos translation
│   ├── tts_engine.py        # Piper/Edge TTS
│   ├── piper_loader.py      # Piper subprocess loader
│   ├── audio_extractor.py   # Audio extraction
│   ├── audio_mixer.py       # numpy audio mixing
│   ├── video_muxer.py       # HLS/WebRTC muxing
│   ├── webrtc_engine.py     # WebRTC engine
│   ├── subtitle_generator.py # VTT generation
│   └── srt_ingest.py        # SRT ingest helper
│
├── server/                  # Servidor HTTP
│   ├── app.py               # FastAPI app + GZip
│   ├── api_routes.py        # REST endpoints
│   ├── ws_routes.py         # WebSocket endpoints
│   └── security.py          # Security middleware
│
├── cli/                     # Herramienta CLI
│   ├── srt2web.py           # CLI completa (540 líneas)
│   ├── srt2web.bat          # Windows launcher
│   └── README.md            # Documentación CLI
│
├── frontend/                # Interfaz web
│   ├── src/
│   │   ├── pages/           # Rutas Astro
│   │   │   ├── index.astro       # Dashboard principal
│   │   │   ├── player.astro      # HLS Player
│   │   │   ├── webrtc-player.astro # WebRTC Player
│   │   │   └── docs/             # Documentación integrada
│   │   ├── components/      # Componentes Astro
│   │   │   ├── ui/          # UI primitives (Button, Input, etc.)
│   │   │   ├── layout/      # Layout components
│   │   │   └── docs/        # Documentation components
│   │   └── lib/             # JavaScript/TypeScript
│   │       ├── store/       # Preact Signals + Effects
│   │       ├── modules/     # UI modules (config, outputs, etc.)
│   │       ├── utils/       # Utilities (clock, format, perf)
│   │       ├── api.ts       # API client + auth
│   │       ├── types.ts     # TypeScript types
│   │       ├── constants.ts # Shared constants
│   │       └── i18n.ts      # Internationalization
│   └── ...
│
├── desktop/                 # App Electron
│   ├── src/main.js          # Electron main process
│   ├── src/preload.js       # Context bridge
│   ├── src/python/          # Python launcher
│   └── ...
│
├── docs/                    # Documentación MkDocs
├── tests/                   # Suite de tests (740 tests)
│   └── unit/                # Tests unitarios
├── scripts/                 # Scripts utilitarios
├── config/                  # Configuración
├── models/                  # Modelos ML descargados
├── output/                  # Directorio de salida
└── logs/                    # Logs de aplicación
```

## Modelo de Datos

```mermaid
erDiagram
    PIPELINE {
        string id PK
        string state
        string mode
        datetime start_time
        datetime end_time
        int processed_chunks
    }

    MODULE {
        string name PK
        string type
        boolean enabled
        string state
        dict config
        dict extra
    }

    CHUNK {
        int index
        string video_path
        string audio_path
        float duration
        float cumulative_duration
        datetime timestamp
    }

    OUTPUT {
        string name PK
        string type
        boolean enabled
        dict config
        string status
        datetime created_at
    }

    PIPELINE ||--o{ MODULE : contains
    PIPELINE ||--o{ CHUNK : processes
    PIPELINE ||--o{ OUTPUT : has_outputs

    OUTPUT }o--|| COMPOSITE : managed_by

    COMPOSITE {
        string id PK
        int active_outputs
        dict output_status
    }
```

## PipelineData

```python
@dataclass
class PipelineData:
    video_chunk_path: Optional[str] = None
    audio_chunk_path: Optional[str] = None
    mixed_audio_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    chunk_index: int = 0
    duration: float = 0.0
    cumulative_duration: float = 0.0
    transcribed_text: Optional[str] = None
    translated_text: Optional[str] = None
    transcribed_segments: Optional[list] = None
    translated_segments: Optional[list] = None
    metadata: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
```
