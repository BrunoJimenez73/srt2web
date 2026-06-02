/**
 * F106 — Piper TTS voice change is ignored in frontend.
 *
 * This test simulates the user changing the voice in the dropdown
 * and verifies the config sent to the API contains the new voice.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";

describe("F106 — Piper voice change end-to-end", () => {
  beforeEach(() => {
    // Build minimal DOM the way the dashboard would have it
    document.body.innerHTML = `
      <select id="input-type"><option value="srt">srt</option></select>
      <input id="input-chunk-duration" value="10" />
      <input id="input-srt-port" value="9000" />
      <select id="input-srt-mode"><option value="listener">listener</option></select>
      <input id="input-srt-latency" value="200" />
      <input id="input-rtmp-chunk" value="10" />
      <input id="input-file-chunk" value="10" />

      <input type="checkbox" id="whisper-enabled" />
      <select id="whisper-model"><option value="base">base</option></select>
      <select id="whisper-lang"><option value="es">es</option></select>
      <select id="whisper-device"><option value="auto">auto</option></select>

      <input type="checkbox" id="translator-enabled" />
      <select id="translator-source"><option value="es">es</option></select>
      <select id="translator-target"><option value="en">en</option></select>

      <input type="checkbox" id="tts-enabled" checked />
      <select id="tts-engine">
        <option value="edge-tts">edge</option>
        <option value="piper">piper</option>
      </select>
      <select id="tts-device"><option value="auto">auto</option></select>
      <select id="tts-voice-edge">
        <option value="es-ES-ElviraNeural">Elvira</option>
      </select>
      <select id="tts-voice-piper">
        <option value="es_ES-sharvard-medium">Sharvard</option>
        <option value="es_ES-davefx-medium">Davefx</option>
        <option value="es_MX-claude-high">Claude</option>
      </select>
      <input id="tts-speed" value="1.0" />

      <input type="checkbox" id="subtitle-enabled" />
      <select id="subtitle-format"><option value="srt">srt</option></select>
      <select id="subtitle-use-translated"><option value="true">true</option></select>

      <input type="checkbox" id="muxer-enabled" />
      <select id="video-muxer-engine"><option value="hls">hls</option></select>
      <input id="hls-segment" value="10" />
      <input id="hls-list" value="3" />
      <input id="hls-audio-offset" value="0" />
      <select id="hls-encoder"><option value="auto">auto</option></select>
      <input id="hls-crf" value="23" />

      <input type="checkbox" id="audio-mixer-enabled" />
      <input id="audio-mixer-original-volume" value="0.2" />
      <input id="audio-mixer-dubbed-volume" value="1.0" />
    `;
  });

  it("collects the new Piper voice when user changes dropdown", async () => {
    const { collectConfigFromUI } = await import("./lib/modules/config-collector");

    // User changes engine to Piper
    (document.getElementById("tts-engine") as HTMLSelectElement).value = "piper";
    // User changes voice to Davefx
    (document.getElementById("tts-voice-piper") as HTMLSelectElement).value =
      "es_ES-davefx-medium";

    const config = collectConfigFromUI();

    expect(config.modules?.tts_engine?.engine).toBe("piper");
    expect(config.modules?.tts_engine?.voice).toBe("es_ES-davefx-medium");
  });

  it("still works when user keeps the default Sharvard voice", async () => {
    const { collectConfigFromUI } = await import("./lib/modules/config-collector");

    (document.getElementById("tts-engine") as HTMLSelectElement).value = "piper";
    // Voice select stays at default (first option = Sharvard)
    (document.getElementById("tts-voice-piper") as HTMLSelectElement).value =
      "es_ES-sharvard-medium";

    const config = collectConfigFromUI();
    expect(config.modules?.tts_engine?.voice).toBe("es_ES-sharvard-medium");
  });

  it("collects Edge-TTS voice when engine is edge-tts", async () => {
    const { collectConfigFromUI } = await import("./lib/modules/config-collector");

    (document.getElementById("tts-engine") as HTMLSelectElement).value = "edge-tts";
    (document.getElementById("tts-voice-edge") as HTMLSelectElement).value =
      "es-ES-ElviraNeural";

    const config = collectConfigFromUI();
    expect(config.modules?.tts_engine?.engine).toBe("edge-tts");
    expect(config.modules?.tts_engine?.voice).toBe("es-ES-ElviraNeural");
  });
});
