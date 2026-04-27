# Arquitectura - SRT2Web

## Diagrama General del Sistema

```mermaid
graph TB
    subgraph OBS["OBS Studio"]
        O_SRT[SRT Output<br/>Port 9000]
    end

    subgraph Server["SRT2Web Server"]
        subgraph Pipeline["Pipeline Core"]
            I_SRT[SRT Input]
            I_RTMP[RTMP Input]
            I_FILE[File Input]
            AE[Audio Extractor]
            TR[Transcriber<br/>Whisper]
            TL[Translator<br/>Argos]
            SG[Subtitle Generator]
            TM[TTS Engine<br/>Piper]
            MX[Audio Mixer]
            VM[Video Muxer<br/>HLS]
        end
        WS[WebSocket<br/>Logs]
        API[REST API]
    end

    subgraph ML["Machine Learning"]
        WHISPER[Whisper<br/>OpenAI]
        ARGOS[Argos Translate<br/>Offline]
        PIPER[Piper TTS<br/>Subprocess]
    end

    subgraph Frontend["Frontend"]
        UI[Dashboard<br/>Astro + Tailwind]
        PLAYER[HLS Player<br/>video.js]
    end

    subgraph Output["Output"]
        HLS[HLS Stream<br/>.m3u8 + .ts]
        WEB[Web UI<br/>localhost:9999]
    end

    O_SRT --> I_SRT
    I_SRT --> AE
    AE --> TR
    TR --> TL
    TL --> SG
    SG --> TM
    TM --> MX
    MX --> VM
    VM --> HLS

    TR --> WHISPER
    TL --> ARGOS
    TM --> PIPER

    I_SRT -.-> WS
    AE -.-> WS
    TR -.-> WS
    TL -.-> WS
    SG -.-> WS
    TM -.-> WS
    MX -.-> WS
    VM -.-> WS

    Server --> WEB
    HLS --> PLAYER

    style OBS fill:#e1f5fe
    style ML fill:#fff3e0
    style Output fill:#e8f5e9
```

## Pipeline de Procesamiento

```mermaid
sequenceDiagram
    participant OBS as OBS Studio
    participant SRT as SRT Input
    participant AE as Audio Extractor
    participant TR as Transcriber
    participant TL as Translator
    participant SG as Subtitle Gen
    participant TTS as TTS Engine
    participant MX as Audio Mixer
    participant VM as Video Muxer

    OBS->>SRT: Stream SRT (port 9000)
    SRT->>SRT: Buffer chunks (10s)
    SRT->>AE: video_chunk_path

    par Extracción de Audio
        AE->>AE: Extract audio track
        AE->>TR: audio_chunk_path
    and Extracción de Video
        SRT->>VM: video_chunk_path
    end

    TR->>TR: Whisper transcription
    TR-->>AE: text transcription

    TL->>TL: Argos translate
    TL-->>TR: translated text

    SG->>SG: Generate VTT subtitles
    SG-->>TTS: subtitle text

    TTS->>TTS: Piper TTS synthesis
    TTS-->>MX: tts_audio.wav

    par Mezcla de Audio
        MX->>MX: Mix original + TTS
        MX-->>VM: mixed_audio.wav
    and Segmentos de Video
        VM->>VM: Create HLS segments
    end

    VM->>VM: Multiplex A/V
    VM->>HLS: .ts segments

    Note over VM: HLS Output<br/>stream.m3u8
```

## Arquitectura de Módulos

```mermaid
classDiagram
    class ModuleBase {
        <<abstract>>
        +enabled: bool
        +state: ModuleState
        +initialize() None
        +process(data: PipelineData) PipelineData
        +get_status() dict
        +shutdown() None
    end

    class InputSource {
        <<interface>>
        +connect() bool
        +disconnect() None
        +read_chunk() Optional~Chunk~
    end

    class OutputSink {
        <<interface>>
        +write(data: Any) bool
        +flush() None
        +close() None
    end

    class SRTInput {
        +port: int
        +latency_ms: int
        +connect() bool
        +read_chunk() Chunk
    }

    class HLSOutput {
        +segment_duration: int
        +write(data: VideoFrame) bool
        +finalize() str
    }

    class Transcriber {
        +model: str
        +device: str
        +transcribe(audio_path: str) str
    }

    class Translator {
        +source_lang: str
        +target_lang: str
        +translate(text: str) str
    }

    class TTSEngine {
        +voice: str
        +speed: float
        +synthesize(text: str) bytes
    }

    class AudioMixer {
        +original_volume: float
        +tts_volume: float
        +mix(audio1: str, audio2: str) str
    }

    class VideoMuxer {
        +encoder: str
        +preset: str
        +mux(video: str, audio: str) str
    }

    ModuleBase <|-- SRTInput
    ModuleBase <|-- Transcriber
    ModuleBase <|-- Translator
    ModuleBase <|-- TTSEngine
    ModuleBase <|-- AudioMixer
    ModuleBase <|-- VideoMuxer

    InputSource <|-- SRTInput
    OutputSink <|-- HLSOutput
```

## Flujo de Datos

```mermaid
flowchart LR
    subgraph Input["Entrada"]
        SRT[SRT Stream]
        RTMP[RTMP Stream]
        FILE[Archivo]
    end

    subgraph Buffer["Buffer de Chunks"]
        B1[Chunk 1]
        B2[Chunk 2]
        B3[Chunk 3]
    end

    subgraph Process["Procesamiento Paralelo"]
        subgraph Audio
            A1[Audio Extract]
            T1[Transcribe]
            L1[Translate]
            S1[Subtitles]
            P1[TTS]
            M1[Mix]
        end
        subgraph Video
            V1[Video Segment]
        end
    end

    subgraph Output["Salida"]
        HLS[HLS Stream]
        WEB[Dashboard]
        WSS[WebSocket]
    end

    SRT --> B1
    SRT --> B2
    SRT --> B3

    B1 --> A1
    B1 --> V1

    A1 --> T1
    T1 --> L1
    L1 --> S1
    S1 --> P1
    P1 --> M1

    V1 --> HLS
    M1 --> HLS

    B1 -.-> WSS
    A1 -.-> WSS
    T1 -.-> WSS
    M1 -.-> WSS
    HLS -.-> WEB

    style Input fill:#e3f2fd
    style Buffer fill:#fff8e1
    style Process fill:#f3e5f5
    style Output fill:#e8f5e9
```

## Arquitectura de Seguridad

```mermaid
flowchart TB
    subgraph Client["Cliente"]
        UI[Browser/Frontend]
        OBS[OBS Studio]
    end

    subgraph Security["Middleware Stack"]
        RH[Rate Limiter<br/>60 req/min]
        AH[Auth Headers]
        SH[Security Headers<br/>CORS, CSP]
        RL[Request Size Limit<br/>10MB]
    end

    subgraph Server["API"]
        WS[WebSocket<br/>Auth Token]
        API[REST API<br/>Auth Token]
    end

    subgraph Backend["Backend"]
        P[Pipeline]
        M[Modules]
        FS[File System]
    end

    UI --> RH
    OBS --> RH

    RH --> AH
    AH --> SH
    SH --> RL

    RL --> WS
    RL --> API

    WS --> P
    API --> P

    P --> M
    M --> FS

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
        Ready --> Processing: process start
        Processing --> Ready: process complete
        Processing --> Error: exception
        Error --> Ready: retry
    }

    Idle --> Processing: start pipeline
    Processing --> Idle: stop pipeline

    state Error {
        [*] --> Recoverable
        Recoverable --> Ready: recovery
        Recoverable --> Fatal: max retries
        Fatal --> [*]: shutdown
    }
```

## Dependencias del Sistema

```mermaid
graph BT
    subgraph Python["Python 3.12"]
        FA[FastAPI]
        PT[PyTorch]
        OR[ONNX Runtime]
    end

    subgraph ML["Machine Learning"]
        WH[Whisper]
        AG[Argos Translate]
        PP[Piper TTS]
    end

    subgraph Video["Video/Audio"]
        FF[FFmpeg]
        NV[NVIDIA CUDA]
    end

    subgraph Front["Frontend"]
        AS[Astro]
        TW[Tailwind CSS]
        VJ[video.js]
    end

    FA --> PT
    PT --> OR
    PT --> NV

    WH --> PT
    AG --> OR
    PP --> OR

    AS --> TW
    AS --> VJ

    style Python fill:#e1f5fe
    style ML fill:#fff3e0
    style Video fill:#e8f5e9
    style Front fill:#f3e5f5
```

## Estructura de Directorios

```
srt2web/
├── core/                    # Núcleo del sistema
│   ├── pipeline.py          # Orquestación del pipeline
│   ├── config_manager.py    # Gestión de configuración
│   ├── module_base.py       # Clase base para módulos
│   ├── ffmpeg_pool.py       # Pool de procesos FFmpeg
│   └── model_cache.py       # Cache de modelos ML
│
├── modules/                 # Módulos de procesamiento
│   ├── inputs/              # Fuentes de entrada
│   │   ├── srt_input.py     # SRT protocol
│   │   └── rtmp_input.py    # RTMP protocol
│   ├── transcriber.py       # Whisper transcription
│   ├── translator.py        # Argos translation
│   ├── tts_engine.py        # Piper TTS
│   ├── audio_mixer.py        # Mezcla de audio (numpy)
│   ├── video_muxer.py        # Multiplexación HLS
│   └── subtitle_generator.py  # Generación VTT
│
├── server/                  # Servidor HTTP
│   ├── app.py               # FastAPI app
│   ├── api_routes.py        # REST endpoints
│   ├── ws_routes.py         # WebSocket endpoints
│   └── security.py          # Middleware seguridad
│
├── frontend/                # Interfaz web
│   └── src/
│       ├── components/      # Componentes Astro
│       ├── lib/             # JavaScript modules
│       └── layouts/          # Layouts base
│
├── desktop/                 # App Electron (opcional)
├── docs/                    # Documentación MkDocs
├── tests/                   # Suite de tests
├── scripts/                 # Scripts utilitarios
└── logs/                    # Logs de aplicación
```

## Modelo de Datos

```mermaid
erDiagram
    PIPELINE {
        string id PK
        string state
        datetime start_time
        datetime end_time
    }

    MODULE {
        string name PK
        string type
        boolean enabled
        string state
        dict config
    }

    CHUNK {
        int index
        string video_path
        string audio_path
        float duration
        datetime timestamp
    }

    PIPELINE ||--o{ MODULE : contains
    PIPELINE ||--o{ CHUNK : processes

    MODULE {
        string name PK
        string type
        boolean enabled
        string state
        dict config
    }

    OUTPUT {
        string id PK
        string type
        string path
        string status
        datetime created_at
    }

    MODULE ||--o{ OUTPUT : produces