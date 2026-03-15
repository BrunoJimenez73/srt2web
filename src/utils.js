const { spawn } = require('child_process');

function spawnWithTimeout(command, args, options = {}, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const proc = spawn(command, args, {
      ...options,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';
    let timedOut = false;

    const timeout = setTimeout(() => {
      timedOut = true;
      proc.kill('SIGTERM');
      setTimeout(() => {
        if (!proc.killed) {
          proc.kill('SIGKILL');
        }
      }, 5000);
    }, timeoutMs);

    proc.stdout?.on('data', (data) => {
      stdout += data;
    });

    proc.stderr.on('data', (data) => {
      stderr += data;
    });

    proc.on('close', (code) => {
      clearTimeout(timeout);
      
      if (timedOut) {
        reject(new Error(`Process timed out after ${timeoutMs}ms`));
        return;
      }

      resolve({
        code,
        stdout,
        stderr,
        proc
      });
    });

    proc.on('error', (err) => {
      clearTimeout(timeout);
      reject(err);
    });
  });
}

function sanitizeFilename(name) {
  return name.replace(/[^a-zA-Z0-9_-]/g, '_');
}

function cleanupTempFiles(files) {
  const fs = require('fs');
  for (const file of files) {
    try {
      if (file && fs.existsSync(file)) {
        fs.unlinkSync(file);
      }
    } catch (err) {
      console.warn(`Failed to delete temp file ${file}:`, err.message);
    }
  }
}

module.exports = {
  spawnWithTimeout,
  sanitizeFilename,
  cleanupTempFiles
};
