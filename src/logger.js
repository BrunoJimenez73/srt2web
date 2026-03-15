const fs = require('fs');
const path = require('path');
const os = require('os');

const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3
};

class Logger {
  constructor(options = {}) {
    this.level = options.level || LOG_LEVELS.INFO;
    this.logDir = options.logDir || path.join(os.homedir(), '.srt-to-web', 'logs');
    this.maxFileSize = options.maxFileSize || 5 * 1024 * 1024;
    this.maxFiles = options.maxFiles || 3;
    this.currentLogFile = null;
    
    this._ensureLogDir();
    this._rotateLog();
  }

  _ensureLogDir() {
    if (!fs.existsSync(this.logDir)) {
      fs.mkdirSync(this.logDir, { recursive: true });
    }
  }

  _getLogFileName() {
    const date = new Date().toISOString().split('T')[0];
    return path.join(this.logDir, `srt-to-web-${date}.log`);
  }

  _rotateLog() {
    this.currentLogFile = this._getLogFileName();
    
    if (fs.existsSync(this.currentLogFile)) {
      const stats = fs.statSync(this.currentLogFile);
      if (stats.size > this.maxFileSize) {
        this._rotateExistingLogs();
      }
    }
  }

  _rotateExistingLogs() {
    const baseName = path.basename(this.currentLogFile, '.log');
    const dirName = path.dirname(this.currentLogFile);
    
    const ext = path.extname(baseName);
    const name = baseName.replace(ext, '');
    
    for (let i = this.maxFiles - 1; i >= 1; i--) {
      const oldFile = path.join(dirName, `${name}.${i}${ext}`);
      const newFile = path.join(dirName, `${name}.${i + 1}${ext}`);
      
      if (fs.existsSync(oldFile)) {
        if (i + 1 > this.maxFiles) {
          fs.unlinkSync(oldFile);
        } else {
          if (fs.existsSync(newFile)) {
            fs.unlinkSync(newFile);
          }
          fs.renameSync(oldFile, newFile);
        }
      }
    }
    
    const firstRotated = path.join(dirName, `${name}.1${path.extname(baseName)}`);
    if (fs.existsSync(this.currentLogFile)) {
      fs.renameSync(this.currentLogFile, firstRotated);
    }
  }

  _formatMessage(level, message, meta = {}) {
    const timestamp = new Date().toISOString();
    const metaStr = Object.keys(meta).length > 0 ? ` ${JSON.stringify(meta)}` : '';
    return `[${timestamp}] [${level}] ${message}${metaStr}\n`;
  }

  _write(formattedMessage) {
    try {
      this._rotateLog();
      fs.appendFileSync(this.currentLogFile, formattedMessage);
    } catch (err) {
      console.error('Failed to write to log file:', err.message);
    }
  }

  debug(message, meta = {}) {
    if (this.level <= LOG_LEVELS.DEBUG) {
      const formatted = this._formatMessage('DEBUG', message, meta);
      this._write(formatted);
      console.debug(message, meta);
    }
  }

  info(message, meta = {}) {
    if (this.level <= LOG_LEVELS.INFO) {
      const formatted = this._formatMessage('INFO', message, meta);
      this._write(formatted);
      console.log(message, meta);
    }
  }

  warn(message, meta = {}) {
    if (this.level <= LOG_LEVELS.WARN) {
      const formatted = this._formatMessage('WARN', message, meta);
      this._write(formatted);
      console.warn(message, meta);
    }
  }

  error(message, meta = {}) {
    if (this.level <= LOG_LEVELS.ERROR) {
      const formatted = this._formatMessage('ERROR', message, meta);
      this._write(formatted);
      console.error(message, meta);
    }
  }

  getLogPath() {
    return this.currentLogFile;
  }
}

const logger = new Logger({
  level: LOG_LEVELS.DEBUG,
  maxFileSize: 10 * 1024 * 1024,
  maxFiles: 5
});

module.exports = { Logger, logger, LOG_LEVELS };
