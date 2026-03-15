const { pipeline, env } = require('@xenova/transformers');

env.allowLocalModels = false;
env.useBrowserCache = false;
env.backends.onnx.wasm.numThreads = 4;

let transcriber = null;

async function initWhisper() {
  if (!transcriber) {
    console.log('Cargando modelo Whisper...');
    transcriber = await pipeline('automatic-speech-recognition', 'Xenova/whisper-small');
    console.log('Modelo Whisper cargado!');
  }
  return transcriber;
}

async function transcribe(audioBuffer) {
  const whisper = await initWhisper();
  const result = await whisper(audioBuffer);
  return result;
}

async function translate(text, sourceLang = 'eng_Latn', targetLang = 'spa_Latn') {
  const translator = await pipeline('translation', 'Xenova/nllb-200-distilled-600M');
  const result = await translator(text, {
    src_lang: sourceLang,
    tgt_lang: targetLang
  });
  return result[0].translation_text;
}

async function test() {
  try {
    console.log('Iniciando test de Whisper...');
    
    // Test translation first (simpler)
    console.log('Testeando traducción...');
    const translated = await translate('Hello, how are you?', 'eng_Latn', 'spa_Latn');
    console.log('Traducción:', translated);
    
    console.log('¡Test completado!');
  } catch (e) {
    console.error('Error:', e.message);
  }
}

test();
