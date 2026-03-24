
import yaml
import os

CONFIG_PATH = "config/config.yaml"

DEFAULT_MODULES = {
    "audio_extractor": {"enabled": True},
    "transcriber": {
        "enabled": True,
        "model": "small",
        "language": "auto",
        "device": "auto",
    },
    "translator": {
        "enabled": True,
        "source_lang": "en",
        "target_lang": "es",
    },
    "subtitle_generator": {
        "enabled": True,
        "format": "webvtt",
        "use_translated": True,
    },
    "tts_engine": {
        "enabled": True, # Forzamos enable para que los veas
        "engine": "edge-tts",
        "voice": "es-ES-AlvaroNeural",
        "speed": 1.0,
        "use_translated": True
    },
    "audio_mixer": {
        "enabled": True, # Forzamos enable
        "original_volume": 0.2,
        "dubbed_volume": 1.0,
    },
    "video_muxer": {
        "enabled": True,
        "hls_segment_duration": 4,
        "hls_list_size": 10,
    }
}

def fix_config():
    if not os.path.exists(CONFIG_PATH):
        print("Config not found")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    if "modules" not in config:
        config["modules"] = {}

    for mod_name, defaults in DEFAULT_MODULES.items():
        if mod_name not in config["modules"]:
            config["modules"][mod_name] = defaults
            print(f"Added missing module: {mod_name}")
        else:
            # Ensure basic fields exist
            for k, v in defaults.items():
                if k not in config["modules"][mod_name]:
                    config["modules"][mod_name][k] = v
                    print(f"Added missing key {k} to {mod_name}")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("Config.yaml fixed and saved!")

if __name__ == "__main__":
    fix_config()
