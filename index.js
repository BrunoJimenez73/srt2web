const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn, spawnSync } = require('child_process');

const DEFAULT_SRT_PORT = 9000;
const DEFAULT_HTTP_PORT = 8089;
const DEFAULT_SRT_URI = 'srt://127.0.0.1:9000?mode=listener';
const PID_FILE = path.join(__dirname, 'server.pid');

const TranslationManager = require('./src/modules/translationManager');

const translationManager = TranslationManager.getInstance();
let subtitles = [];

function parseArgs() {
  const args = process.argv.slice(2);
  const config = {
    srtUri: null,
    port: DEFAULT_HTTP_PORT,
    help: false,
    stop: false,
    translate: true,
    lang: 'spa'
  };
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '-h' || arg === '--help') {
      config.help = true;
    } else if (arg === '--stop') {
      config.stop = true;
    } else if (arg === '--no-translate') {
      config.translate = false;
    } else if (arg === '--lang') {
      config.lang = args[++i];
    } else if (arg === '-s' || arg === '--srt') {
      config.srtUri = args[++i];
    } else if (arg === '-p' || arg === '--port') {
      config.port = parseInt(args[++i], 10);
    } else if (arg === '-r' || arg === '--rtmp') {
      config.srtUri = args[++i];
    }
  }
  
  return config;
}

function printHelp() {
  console.log(`
SRT/RTMP to HLS Stream Server with STT & Translation
=====================================================

Usage: node index.js [options]

Options:
  -s, --srt <uri>      SRT URI (e.g., srt://127.0.0.1:9000?mode=listener)
  -r, --rtmp <uri>     RTMP URL (e.g., rtmp://localhost:1935/live/test)
  -p, --port <port>    HTTP port for HLS stream (default: 8089)
  --lang <code>        Target language for translation (default: spa)
  --no-translate       Disable translation (STT only)
  --stop                Stop the running server
  -h, --help           Show this help

Examples:
  node index.js --srt "srt://127.0.0.1:9000?mode=listener"
  node index.js --rtmp "rtmp://localhost:1935/live/test" --lang spa

Output:
  When started, open: http://localhost:<port>/stream.html
  Subtitles: http://localhost:<port>/subtitles.vtt
`);
}

class StreamServer {
  constructor(config) {
    this.config = config;
    this.server = null;
    this.outputDir = null;
    this.ffmpegProcess = null;
    this.ffmpegAudioProcess = null;
    this.isRunning = false;
    this.processingQueue = [];
    this.isProcessing = false;
    this.audioBuffer = [];
    this.lastSubtitle = '';
  }

  async start() {
    if (this.isRunning) throw new Error('Already running');

    await translationManager.initialize({
      targetLang: this.config.lang,
      translate: this.config.translate
    });
    
    const port = this.config.port;
    const streamUri = this.config.srtUri;
    
    if (!streamUri) {
      throw new Error('No stream URI provided. Use --srt or --rtmp');
    }
    
    const isSrt = streamUri.startsWith('srt://');
    const isRtmp = streamUri.startsWith('rtmp://');
    
    if (!isSrt && !isRtmp) {
      throw new Error('URI must start with srt:// or rtmp://');
    }
    
    this.outputDir = path.join(os.tmpdir(), `hls_${Date.now()}`);
    fs.mkdirSync(this.outputDir, { recursive: true });
    
    console.log(`\n=== SRT/RTMP to HLS Stream Server ===`);
    console.log(`Stream URI: ${streamUri}`);
    console.log(`HTTP Port:  ${port}`);
    console.log(`Output Dir: ${this.outputDir}`);
    console.log(`Translation: ${this.config.translate ? 'Enabled (' + this.config.lang + ')' : 'Disabled'}`);
    console.log(`=======================================\n`);

    const ffmpegStatic = require('ffmpeg-static');

    const args = [
      '-hide_banner',
      '-loglevel', 'error',
      '-re',
      '-fflags', '+genpts+discardcorrupt',
      '-i', streamUri,
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-b:a', '96k',
      '-ar', '44100',
      '-f', 'hls',
      '-hls_time', '2',
      '-hls_list_size', '15',
      '-hls_flags', 'append_list+omit_endlist+discont_start',
      '-hls_segment_filename', path.join(this.outputDir, 'seg_%03d.ts'),
      '-hls_allow_cache', '0',
      '-muxdelay', '0',
      '-muxpreload', '0',
      '-max_delay', '500000',
      path.join(this.outputDir, 'stream.m3u8')
    ];

    console.log('Starting FFmpeg (video + audio)...');

    this.ffmpegProcess = spawn(ffmpegStatic, args, { stdio: ['pipe', 'pipe', 'pipe'] });

    this.ffmpegProcess.stderr.on('data', d => {
      process.stderr.write(d.toString());
    });

    this.ffmpegProcess.on('close', c => {
      console.log(`FFmpeg closed: ${c}`);
      if (this.isRunning) {
        console.log('FFmpeg ended, restarting in 2 seconds...');
        setTimeout(() => this._restartFFmpeg(), 2000);
      }
    });

    this.ffmpegProcess.on('error', e => {
      console.error(`FFmpeg error: ${e.message}`);
    });

    await this._waitForSegments(3).catch(() => {
      console.log('No stream yet, server will retry...');
    });

    this._startAudioCapture();
    this._generateSubtitlesLoop();

    this.server = http.createServer((req, res) => {
      let urlPath = req.url.split('?')[0];
      
      if (urlPath === '/player') {
        res.writeHead(302, { 'Location': '/stream.html' });
        res.end();
        return;
      }
      
      if (urlPath === '/subtitles.vtt') {
        res.writeHead(200, { 'Content-Type': 'text/vtt', 'Access-Control-Allow-Origin': '*' });
        res.end(this._generateVTT());
        return;
      }
      
      if (urlPath === '/') urlPath = '/stream.html';
      
      const filePath = path.join(this.outputDir, urlPath);
      const normPath = path.normalize(filePath).replace(/\\/g, '/');
      const normDir = path.normalize(this.outputDir).replace(/\\/g, '/');
      
      if (!normPath.startsWith(normDir)) {
        res.writeHead(403); 
        res.end('Forbidden'); 
        return;
      }

      fs.stat(filePath, (err, stats) => {
        if (err || !stats.isFile()) {
          if (urlPath === '/stream.html') {
            this._servePlayer(res, port);
          } else {
            res.writeHead(404); 
            res.end('Not found');
          }
          return;
        }

        const ext = path.extname(urlPath).toLowerCase();
        
        if (ext === '.ts' && req.headers.range) {
          const range = req.headers.range;
          const parts = range.replace(/bytes=/, '').split('-');
          const start = parseInt(parts[0]) || 0;
          const end = parseInt(parts[1]) || stats.size - 1;
          
          res.writeHead(206, {
            'Content-Range': `bytes ${start}-${end}/${stats.size}`,
            'Accept-Ranges': 'bytes',
            'Content-Length': end - start + 1,
            'Content-Type': 'video/mp2t',
            'Access-Control-Allow-Origin': '*'
          });
          fs.createReadStream(filePath, { start, end }).pipe(res);
          return;
        }

        const types = { 
          '.m3u8': 'application/vnd.apple.mpegurl', 
          '.ts': 'video/mp2t', 
          '.html': 'text/html' 
        };
        
        fs.readFile(filePath, (err, data) => {
          if (err) { res.writeHead(500); res.end(); return; }
          res.writeHead(200, { 
            'Content-Type': types[ext] || 'application/octet-stream', 
            'Access-Control-Allow-Origin': '*' 
          });
          res.end(data);
        });
      });
    });

    this.server.listen(port, () => {
      fs.writeFileSync(PID_FILE, process.pid.toString());
      const streamUrl = `http://localhost:${port}/stream.html`;
      console.log(`\n=== Server ready! ===`);
      console.log(`Stream URL: ${streamUrl}`);
      console.log(`Subtitles: http://localhost:${port}/subtitles.vtt`);
      console.log(`\nPress Ctrl+C to stop\n`);
      this._servePlayerHtml(port);
    });

    this.isRunning = true;
    return this.startedUrl || `http://localhost:${port}/stream.html`;
  }

  _startAudioCapture() {
    const ffmpegStatic = require('ffmpeg-static');
    
    console.log('Starting audio capture for STT...');
    
    let lastSegment = 0;
    
    const captureAudio = () => {
      if (!this.isRunning) return;
      
      const files = fs.readdirSync(this.outputDir).filter(f => f.startsWith('seg_') && f.endsWith('.ts'));
      if (files.length === 0) {
        setTimeout(captureAudio, 2000);
        return;
      }
      
      const latestFile = files.sort().pop();
      const currentNum = parseInt(latestFile.replace('seg_', '').replace('.ts', ''));
      
      if (currentNum > lastSegment) {
        lastSegment = currentNum;
        const audioFile = path.join(this.outputDir, `audio_${Date.now()}.wav`);
        const inputFile = path.join(this.outputDir, latestFile);
        
        const captureArgs = [
          '-hide_banner',
          '-loglevel', 'error',
          '-i', inputFile,
          '-ac', '1',
          '-ar', '16000',
          '-acodec', 'pcm_s16le',
          '-y',
          audioFile
        ];
        
        const proc = spawn(ffmpegStatic, captureArgs, { stdio: ['pipe', 'pipe', 'pipe'] });
        
        proc.on('close', (code) => {
          if (code === 0 && fs.existsSync(audioFile)) {
            const stats = fs.statSync(audioFile);
            if (stats.size > 1000) {
              this.processingQueue.push(audioFile);
              this._processQueue();
            }
          }
        });
      }
      
      setTimeout(captureAudio, 3000);
    };
    
    setTimeout(captureAudio, 5000);
  }

  async _processQueue() {
    if (this.isProcessing || this.processingQueue.length === 0) return;
    
    this.isProcessing = true;
    const audioFile = this.processingQueue.shift();
    
    try {
      const result = await translationManager.process({ audioFile }, { translate: this.config.translate });
      
      if (result && result.translatedText) {
        subtitles.push({
          timestamp: Date.now() / 1000,
          text: result.originalText,
          translated: result.translatedText
        });
        
        if (subtitles.length > 100) {
          subtitles.shift();
        }
      }
    } catch (e) {
      console.error('Error processing audio:', e.message);
    }
    
    try {
      fs.unlinkSync(audioFile);
    } catch (e) {}
    
    this.isProcessing = false;
    
    if (this.processingQueue.length > 0) {
      this._processQueue();
    }
  }

  _generateSubtitlesLoop() {
    const updateSubtitles = () => {
      if (!this.isRunning) return;
      
      const vttPath = path.join(this.outputDir, 'subtitles.vtt');
      fs.writeFileSync(vttPath, this._generateVTT());
      
      setTimeout(updateSubtitles, 2000);
    };
    
    setTimeout(updateSubtitles, 5000);
  }

  _generateVTT() {
    return translationManager.generateVTT(subtitles, 20);
  }

  _restartFFmpeg() {
    if (!this.isRunning) return;
    
    const ffmpegStatic = require('ffmpeg-static');
    const args = [
      '-hide_banner',
      '-loglevel', 'error',
      '-re',
      '-fflags', '+genpts+discardcorrupt',
      '-i', this.config.srtUri,
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-b:a', '96k',
      '-ar', '44100',
      '-f', 'hls',
      '-hls_time', '2',
      '-hls_list_size', '15',
      '-hls_flags', 'append_list+omit_endlist+discont_start',
      '-hls_segment_filename', path.join(this.outputDir, 'seg_%03d.ts'),
      '-hls_allow_cache', '0',
      '-muxdelay', '0',
      '-muxpreload', '0',
      '-max_delay', '500000',
      path.join(this.outputDir, 'stream.m3u8')
    ];

    console.log('Restarting FFmpeg...');
    
    this.ffmpegProcess = spawn(ffmpegStatic, args, { stdio: ['pipe', 'pipe', 'pipe'] });

    this.ffmpegProcess.stderr.on('data', d => {
      process.stderr.write(d.toString());
    });

    this.ffmpegProcess.on('close', c => {
      if (this.isRunning) {
        console.log('FFmpeg closed, restarting...');
        setTimeout(() => this._restartFFmpeg(), 2000);
      }
    });

    this.ffmpegProcess.on('error', e => {
      console.error(`FFmpeg error: ${e.message}`);
    });

    this._waitForSegments(3).catch(() => {});
  }

  async _waitForSegments(min) {
    const playlistPath = path.join(this.outputDir, 'stream.m3u8');
    const timeout = 15000;
    const start = Date.now();
    
    console.log('Waiting for HLS segments...');
    
    while (Date.now() - start < timeout) {
      try {
        if (fs.existsSync(playlistPath)) {
          const segs = fs.readdirSync(this.outputDir).filter(f => f.endsWith('.ts'));
          process.stdout.write(`\rSegments: ${segs.length}/${min}... `);
          if (segs.length >= min) {
            console.log('\nSegments ready!');
            await new Promise(r => setTimeout(r, 500));
            return true;
          }
        }
      } catch (e) {}
      await new Promise(r => setTimeout(r, 500));
    }
    throw new Error('Timeout waiting for HLS segments');
  }

  _servePlayer(res, port) {
    res.writeHead(200, { 'Content-Type': 'text/html', 'Access-Control-Allow-Origin': '*' });
    res.end(`<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>SRT Stream</title>
<link href="https://vjs.zencdn.net/8.12.0/video-js.css" rel="stylesheet">
<style>
body{margin:0;background:#000;display:flex;align-items:center;justify-content:center;min-height:100vh}
video{width:100%;height:100%;max-width:100vw;max-height:100vh}
.video-js{width:100%!important;height:100%!important}
</style></head>
<body><video id="v" class="video-js vjs-fill" controls playsinline preload="auto">
<source src="http://localhost:${port}/stream.m3u8" type="application/x-mpegURL">
<track kind="subtitles" label="Español" srclang="es" src="http://localhost:${port}/subtitles.vtt" default>
</video>
<script src="https://vjs.zencdn.net/8.12.0/video.min.js"></script>
<script>videojs('v', {fill: true})</script></body></html>`);
  }

  _servePlayerHtml(port) {
    const html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>SRT to Web Stream</title>
<link href="https://vjs.zencdn.net/8.12.0/video-js.css" rel="stylesheet">
<style>
body{margin:0;background:#000;display:flex;align-items:center;justify-content:center;min-height:100vh}
video{width:100%;height:100%;max-width:100vw;max-height:100vh}
.video-js{width:100%!important;height:100%!important}
</style></head>
<body><video id="v" class="video-js vjs-fill" controls playsinline preload="auto">
<source src="http://localhost:${port}/stream.m3u8" type="application/x-mpegURL">
<track kind="subtitles" label="Español" srclang="es" src="http://localhost:${port}/subtitles.vtt" default>
</video>
<script src="https://vjs.zencdn.net/8.12.0/video.min.js"></script>
<script>videojs('v', {fill: true})</script></body></html>`;
    fs.writeFileSync(path.join(this.outputDir, 'stream.html'), html);
  }

  async stop() {
    if (!this.isRunning) return;
    this.isRunning = false;
    console.log('\nStopping server...');

    if (this.ffmpegProcess) {
      this.ffmpegProcess.kill('SIGTERM');
      setTimeout(() => { 
        if (!this.ffmpegProcess.killed) this.ffmpegProcess.kill('SIGKILL'); 
      }, 2000);
    }
    if (this.server) this.server.close();
    if (this.outputDir && fs.existsSync(this.outputDir)) {
      try { fs.rmSync(this.outputDir, { recursive: true, force: true }); } catch(e) {}
    }
    console.log('Server stopped.');
  }
}

async function stopServer() {
  if (!fs.existsSync(PID_FILE)) {
    console.log('No server running (no PID file found)');
    process.exit(0);
  }
  const pid = parseInt(fs.readFileSync(PID_FILE, 'utf8'));
  try {
    process.kill(pid, 'SIGTERM');
    console.log(`Sent SIGTERM to process ${pid}`);
    fs.unlinkSync(PID_FILE);
    console.log('Server stopped');
  } catch (e) {
    console.log(`Error stopping server: ${e.message}`);
    if (fs.existsSync(PID_FILE)) fs.unlinkSync(PID_FILE);
  }
  process.exit(0);
}

async function main() {
  const config = parseArgs();
  
  if (config.help) {
    printHelp();
    process.exit(0);
  }

  if (config.stop) {
    await stopServer();
    return;
  }

  if (!config.srtUri) {
    config.srtUri = DEFAULT_SRT_URI;
  }

  const server = new StreamServer(config);

  process.on('SIGINT', () => {
    console.log('\nReceived Ctrl+C, shutting down...');
    server.stop();
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    server.stop();
    process.exit(0);
  });

  try {
    await server.start();
  } catch (err) {
    console.error(`Error: ${err.message}`);
    printHelp();
    process.exit(1);
  }
}

main();
