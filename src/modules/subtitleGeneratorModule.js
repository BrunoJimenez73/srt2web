const path = require('path');
const os = require('os');
const fs = require('fs');
const BaseModule = require('./baseModule');
const { cleanupTempFiles } = require('../utils');

class SubtitleGeneratorModule extends BaseModule {
  constructor() {
    super();
    this.tempFiles = [];
  }

  /**
   * @param {Object} input - Contains the translated JSON file path
   * @param {Object} config - Configuration (not used yet)
   * @returns {Promise<{vttFile: string}>}
   */
  async process(input, config) {
    const { translatedJson } = input;
    const sttData = JSON.parse(fs.readFileSync(translatedJson, 'utf8'));

    const segments = sttData.segments;
    if (!Array.isArray(segments)) {
      throw new Error('Translated JSON does not contain a segments array');
    }

    const vttFile = path.join(os.tmpdir(), `subtitles_${Date.now()}.vtt`);
    this.tempFiles.push(vttFile);

    let vttContent = 'WEBVTT\n\n';

    segments.forEach((segment, index) => {
      const formatTimestamp = (seconds) => {
        const date = new Date(seconds * 1000);
        const hours = date.getUTCHours().toString().padStart(2, '0');
        const minutes = date.getUTCMinutes().toString().padStart(2, '0');
        const secs = date.getUTCSeconds().toString().padStart(2, '0');
        const milliseconds = date.getUTCMilliseconds().toString().padStart(3, '0');
        return `${hours}:${minutes}:${secs}.${milliseconds}`;
      };

      const start = formatTimestamp(segment.start);
      const end = formatTimestamp(segment.end);
      const text = (segment.text || '').replace(/\n/g, ' ');

      vttContent += `${index + 1}\n`;
      vttContent += `${start} --> ${end}\n`;
      vttContent += `${text}\n\n`;
    });

    fs.writeFileSync(vttFile, vttContent);

    return { vttFile };
  }

  async cleanup(moduleInstance) {
    cleanupTempFiles([moduleInstance.vttFile, ...this.tempFiles]);
  }
}

module.exports = SubtitleGeneratorModule;
