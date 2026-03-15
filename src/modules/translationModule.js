const fs = require('fs');
const path = require('path');
const os = require('os');
const { Pipeline } = require('@xenova/transformers');
const BaseModule = require('./baseModule');
const { cleanupTempFiles } = require('../utils');

class TranslationModule extends BaseModule {
  constructor() {
    super();
    this.translator = null;
    this.modelName = 'Xenova/nllb-200-distilled-600M';
    this.tempFiles = [];
  }

  async initialize(config) {
    if (config.useOnline) {
      console.warn('Online translation not implemented. Using offline model.');
    }

    if (!this.translator || this.translator.modelName !== this.modelName) {
      console.log(`Loading translation model: ${this.modelName}`);
      this.translator = await Pipeline.fetch('translation', this.modelName);
    }

    this.sourceLang = config.sourceLang;
    this.targetLang = config.targetLang;
  }

  /**
   * @param {Object} input - Contains the STT JSON file path
   * @param {Object} config - Configuration for translation
   * @param {number} [config.timeout=300000] - Timeout for translation in ms
   * @returns {Promise<{translatedJson: string}>}
   */
  async process(input, config) {
    const timeout = config.timeout || 300000;
    const startTime = Date.now();

    await this.initialize(config);

    const { sttJson } = input;
    const sttData = JSON.parse(fs.readFileSync(sttJson, 'utf8'));

    if (sttData.segments && Array.isArray(sttData.segments)) {
      for (const segment of sttData.segments) {
        if (Date.now() - startTime > timeout) {
          throw new Error(`Translation timeout after ${timeout}ms`);
        }
        
        if (segment.text && segment.text.trim()) {
          try {
            const result = await this.translator(segment.text, {
              source_lang: this.sourceLang,
              target_lang: this.targetLang
            });
            segment.text = result[0].translation_text;
          } catch (err) {
            console.warn(`Failed to translate segment: ${err.message}`);
          }
        }
      }
    } else if (sttData.text) {
      const result = await this.translator(sttData.text, {
        source_lang: this.sourceLang,
        target_lang: this.targetLang
      });
      sttData.text = result[0].translation_text;
    }

    const outputJson = path.join(os.tmpdir(), `translated_${Date.now()}.json`);
    this.tempFiles.push(outputJson);
    fs.writeFileSync(outputJson, JSON.stringify(sttData, null, 2));

    return { translatedJson: outputJson };
  }

  async cleanup(moduleInstance) {
    cleanupTempFiles([moduleInstance.translatedJson, ...this.tempFiles]);
  }
}

module.exports = TranslationModule;
