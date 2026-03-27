#!/usr/bin/env python3
"""
Download all Piper TTS voice models required by srt2web.
Run this script once to download all voices.
"""

import os
import urllib.request
import urllib.error

VOICES_TO_DOWNLOAD = [
    # English
    (
        "en_US-amy-low",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/low/en_US-amy-low.onnx",
    ),
    (
        "en_US-ryan-low",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/low/en_US-ryan-low.onnx",
    ),
    # Spanish (Spain)
    (
        "es_ES-mls_10246-low",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls_10246/low/es_ES-mls_10246-low.onnx",
    ),
    (
        "es_ES-davefx-medium",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
    ),
    (
        "es_ES-sharvard-medium",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx",
    ),
    # Spanish (Mexico)
    (
        "es_MX-claude-high",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claude/high/es_MX-claude-high.onnx",
    ),
    # Spanish (Argentina)
    (
        "es_AR-daniela-high",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx",
    ),
    # French
    (
        "fr_FR-siwis-medium",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx",
    ),
    (
        "fr_FR-gilles-low",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/gilles/low/fr_FR-gilles-low.onnx",
    ),
    # German
    (
        "de_DE-eva_k-x_low",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/eva_k/x_low/de_DE-eva_k-x_low.onnx",
    ),
    (
        "de_DE-thorsten-medium",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx",
    ),
    # Italian
    (
        "it_IT-paola-medium",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx",
    ),
    (
        "it_IT-riccardo-x_low",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx",
    ),
    # Portuguese
    (
        "pt_BR-cadu-medium",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/cadu/medium/pt_BR-cadu-medium.onnx",
    ),
    (
        "pt_PT-tugao-medium",
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_PT/tug%C3%A3o/medium/pt_PT-tuga%C3%A3o-medium.onnx",
    ),
]


def get_models_dir():
    """Get the models directory path."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "models", "piper")


def download_file(url, dest_path, voice_name):
    """Download a file with progress indication."""
    try:
        print(f"  Downloading {voice_name}...")
        print(f"    URL: {url}")

        # Create request with user agent to avoid 403 errors
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )

        with urllib.request.urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 8192

            with open(dest_path, "wb") as f:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    f.write(buffer)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(
                            f"\r    Progress: {percent:.1f}% ({downloaded // (1024 * 1024)}MB / {total_size // (1024 * 1024)}MB)",
                            end="",
                        )

        print(f"\n  [OK] Downloaded: {dest_path}")
        return True

    except urllib.error.HTTPError as e:
        print(f"  [ERROR] HTTP Error {e.code}: {e.reason} for {url}")
        return False
    except urllib.error.URLError as e:
        print(f"  [ERROR] URL Error: {e.reason} for {url}")
        return False
    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        return False


def download_model(voice_name, base_url):
    """Download both .onnx and .onnx.json files for a voice."""
    models_dir = get_models_dir()
    os.makedirs(models_dir, exist_ok=True)

    onnx_path = os.path.join(models_dir, f"{voice_name}.onnx")
    json_path = os.path.join(models_dir, f"{voice_name}.onnx.json")

    # Check if already exists
    if os.path.exists(onnx_path) and os.path.exists(json_path):
        size = os.path.getsize(onnx_path) // (1024 * 1024)
        print(f"  [OK] Already exists: {voice_name} ({size}MB)")
        return True

    print(f"\nDownloading {voice_name}...")

    # Download .onnx file
    onnx_url = base_url
    if not download_file(onnx_url, onnx_path, voice_name):
        return False

    # Download .onnx.json file
    json_url = base_url + ".json"
    json_dest = os.path.join(models_dir, f"{voice_name}.onnx.json")
    if not download_file(json_url, json_dest, f"{voice_name} (config)"):
        # If JSON fails, try alternate URL format
        json_url_alt = base_url.replace(".onnx", ".onnx.json")
        if json_url_alt != json_url:
            if not download_file(
                json_url_alt, json_dest, f"{voice_name} (config - alt)"
            ):
                print(f"  [WARNING] Could not download config file for {voice_name}")
                # Don't fail completely if config is missing
                return True

    return True


def main():
    print("=" * 60)
    print("Piper TTS Voice Model Downloader")
    print("=" * 60)
    print(f"\nModels directory: {get_models_dir()}")
    print(f"Total voices to download: {len(VOICES_TO_DOWNLOAD)}")
    print()

    successful = 0
    failed = []

    for voice_name, url in VOICES_TO_DOWNLOAD:
        if download_model(voice_name, url):
            successful += 1
        else:
            failed.append(voice_name)
        print()

    print("=" * 60)
    print("Download Summary")
    print("=" * 60)
    print(f"  Successful: {successful}/{len(VOICES_TO_DOWNLOAD)}")

    if failed:
        print(f"  Failed: {', '.join(failed)}")
        print("\nYou may need to download these manually from:")
        for voice_name, url in VOICES_TO_DOWNLOAD:
            if voice_name in failed:
                print(f"  - {voice_name}: {url}")
    else:
        print("  All voices downloaded successfully!")

    print()
    print("You can now use these voices in srt2web with Piper TTS.")


if __name__ == "__main__":
    main()
