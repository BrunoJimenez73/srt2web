const { pipeline, env } = require('@xenova/transformers');
const path = require('path');
const os = require('os');
const fs = require('fs');
const BaseModule = require('./baseModule');
const { cleanupTempFiles } = require('../utils');

env.allowLocalModels = false;
env.useBrowserCache = false;

const PIPELINE_OPTIONS = {
  device: 'cpu',
  dtype: 'q8',
};

class TranslationManager extends BaseModule {
  constructor() {
    super();
    this.whisperModel = null;
    this.translatorModel = null;
    this.targetLang = 'spa';
    this.sourceLang = 'eng';
    this.tempFiles = [];
    this.isInitialized = false;
  }

  async initialize(config = {}) {
    this.targetLang = config.targetLang || 'spa';
    this.sourceLang = config.sourceLang || 'eng';

    const targetLangCode = this.targetLang + '_Latn';
    const sourceLangCode = this.sourceLang + '_Latn';

    if (!this.whisperModel) {
      console.log('[TranslationManager] Cargando modelo Whisper (CPU)...');
      this.whisperModel = await pipeline('automatic-speech-recognition', 'Xenova/whisper-small', PIPELINE_OPTIONS);
      console.log('[TranslationManager] Whisper cargado!');
    }

    if (!this.translatorModel) {
      console.log('[TranslationManager] Cargando modelo de traducción (CPU)...');
      this.translatorModel = await pipeline('translation', 'Xenova/nllb-200-distilled-600M', PIPELINE_OPTIONS);
      console.log('[TranslationManager] Traductor cargado!');
    }

    this.isInitialized = true;
  }

  async process(input, config = {}) {
    if (!this.isInitialized) {
      await this.initialize(config);
    }

    const { audioFile } = input;
    const enableTranslation = config.translate !== false;

    if (!audioFile || !fs.existsSync(audioFile)) {
      throw new Error(`Audio file not found: ${audioFile}`);
    }

    const stats = fs.statSync(audioFile);
    if (stats.size < 1000) {
      console.log('[TranslationManager] Audio file too small, skipping');
      return { text: null, translated: null };
    }

    console.log('[TranslationManager] Transcribiendo audio...');
    const sttResult = await this.whisperModel(audioFile);
    const originalText = sttResult.text;

    if (!originalText || originalText.trim() === '') {
      return { text: null, translated: null };
    }

    console.log('[TranslationManager] Original:', originalText);

    let translatedText = originalText;

    if (enableTranslation) {
      try {
        const targetLangCode = this.targetLang + '_Latn';
        const sourceLangCode = this.sourceLang + '_Latn';

        const transResult = await this.translatorModel(originalText, {
          src_lang: sourceLangCode,
          tgt_lang: targetLangCode
        });

        translatedText = transResult[0].translation_text;
        console.log('[TranslationManager] Traducido:', translatedText);
      } catch (err) {
        console.error('[TranslationManager] Error en traducción:', err.message);
        translatedText = originalText;
      }
    }

    const outputJson = path.join(os.tmpdir(), `transcription_${Date.now()}.json`);
    this.tempFiles.push(outputJson);

    const result = {
      text: originalText,
      translated: enableTranslation ? translatedText : null,
      timestamp: Date.now() / 1000
    };

    fs.writeFileSync(outputJson, JSON.stringify(result, null, 2));

    return {
      originalText,
      translatedText,
      jsonFile: outputJson
    };
  }

  generateVTT(subtitles, maxEntries = 20) {
    let vtt = 'WEBVTT\n\n';

    if (!subtitles || subtitles.length === 0) {
      vtt += '1\n00:00:00.000 --> 00:00:02.000\nEsperando subtítulos...\n';
      return vtt;
    }

    const recentSubtitles = subtitles.slice(-maxEntries);
    let index = 1;

    for (const sub of recentSubtitles) {
      const start = new Date(sub.timestamp * 1000).toISOString().substr(11, 12);
      const end = new Date((sub.timestamp + 3) * 1000).toISOString().substr(11, 12);
      const text = sub.translated || sub.text || '';
      vtt += `${index}\n${start} --> ${end}\n${text}\n\n`;
      index++;
    }

    return vtt;
  }

  async cleanup(instance) {
    cleanupTempFiles([...this.tempFiles, instance.jsonFile].filter(Boolean));
  }

  static getInstance() {
    if (!TranslationManager.instance) {
      TranslationManager.instance = new TranslationManager();
    }
    return TranslationManager.instance;
  }
}

module.exports = TranslationManager;
