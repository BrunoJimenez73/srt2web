const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');
const BaseModule = require('./baseModule');
const { spawnWithTimeout, cleanupTempFiles } = require('../utils');

class SttModule extends BaseModule {
  constructor() {
    super();
    this.tempFiles = [];
  }

  /**
   * @param {Object} input - Contains the audio file path from the previous module
   * @param {Object} config - Configuration for STT
   * @param {string} [config.language='auto'] - Language code or 'auto' for detection
   * @param {number} [config.threads=4] - Number of threads to use
   * @param {number} [config.timeout=180000] - Timeout in ms (default 3 min)
   * @returns {Promise<{sttJson: string, detectedLanguage: string}>}
   */
  async process(input, config) {
    const { audioFile } = input;
    const { language = 'auto', threads = 4, timeout = 180000 } = config;

    const outputJson = path.join(os.tmpdir(), `stt_${Date.now()}.json`);
    this.tempFiles.push(outputJson);

    const args = [
      '-m', config.modelPath || 'base',
      '-f', audioFile,
      '--output-json',
      '-t', threads.toString(),
      ...(language !== 'auto' ? ['-l', language] : [])
    ];

    const whisperBinary = config.whisperBinary || 'whisper-cli';

    const result = await spawnWithTimeout(whisperBinary, args, {}, timeout);

    if (result.code !== 0) {
      throw new Error(`Whisper.cpp failed with code ${result.code}: ${result.stderr}`);
    }

    if (!fs.existsSync(outputJson)) {
      throw new Error('Whisper.cpp did not produce output file');
    }

    let detectedLanguage = language;
    if (language === 'auto') {
      const match = result.stderr.match(/whisper_detect_language: auto \(using (\w+)\)/);
      detectedLanguage = match?.[1]?.toLowerCase() || 'en';
    }

    return { sttJson: outputJson, detectedLanguage };
  }

  async cleanup(moduleInstance) {
    cleanupTempFiles([moduleInstance.sttJson, ...this.tempFiles]);
  }
}

module.exports = SttModule;
