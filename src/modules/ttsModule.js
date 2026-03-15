const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');
const BaseModule = require('./baseModule');
const { spawnWithTimeout, cleanupTempFiles } = require('../utils');

class TtsModule extends BaseModule {
  constructor() {
    super();
    this.tempFiles = [];
  }

  /**
   * @param {Object} input - Contains the translated JSON file path
   * @param {Object} config - Configuration for TTS
   * @param {number} [config.timeout=120000] - Timeout in ms
   * @returns {Promise<{ttsWav: string}>}
   */
  async process(input, config) {
    const timeout = config.timeout || 120000;
    const { translatedJson } = input;
    
    const translatedData = JSON.parse(fs.readFileSync(translatedJson, 'utf8'));

    let textToSpeak = '';
    if (translatedData.text) {
      textToSpeak = translatedData.text;
    } else if (translatedData.segments && Array.isArray(translatedData.segments)) {
      textToSpeak = translatedData.segments.map(seg => seg.text).join(' ');
    } else {
      throw new Error('Translated JSON does not contain text or segments');
    }

    const outputWav = path.join(os.tmpdir(), `tts_${Date.now()}.wav`);
    this.tempFiles.push(outputWav);

    const platform = process.platform;

    if (platform === 'win32') {
      const escapedText = textToSpeak.replace(/"/g, '`"').replace(/\r?\n/g, ' ');
      const psScript = `
        Add-Type -AssemblyName System.Speech;
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;
        $synth.SetOutputToWaveFile("${outputWav.replace(/\\/g, '\\\\')}");
        $synth.Speak("${escapedText}");
        $synth.Dispose();
      `;
      
      const result = await spawnWithTimeout('powershell', ['-NoProfile', '-Command', psScript], {}, timeout);
      
      if (result.code !== 0) {
        throw new Error(`PowerShell TTS failed: ${result.stderr}`);
      }
    } else if (platform === 'darwin') {
      const tempAiff = path.join(os.tmpdir(), `tts_${Date.now()}.aiff`);
      this.tempFiles.push(tempAiff);
      
      const result = await spawnWithTimeout('say', ['-o', tempAiff, '--data-format=LEF32@22050', textToSpeak], {}, timeout);
      
      if (result.code !== 0) {
        throw new Error(`say command failed: ${result.stderr}`);
      }
      
      const convResult = await spawnWithTimeout('ffmpeg', ['-y', '-i', tempAiff, outputWav], {}, timeout);
      
      if (convResult.code !== 0) {
        throw new Error(`FFmpeg conversion failed: ${convResult.stderr}`);
      }
    } else {
      const result = await spawnWithTimeout('espeak', ['-w', outputWav, textToSpeak], {}, timeout);
      
      if (result.code !== 0) {
        throw new Error(`espeak failed: ${result.stderr}`);
      }
    }

    return { ttsWav: outputWav };
  }

  async cleanup(moduleInstance) {
    cleanupTempFiles([moduleInstance.ttsWav, ...this.tempFiles]);
  }
}

module.exports = TtsModule;
