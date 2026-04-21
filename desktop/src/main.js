/**
 * SRT2Web Desktop - Main Process
 * 
 * Electron main process que:
 * 1. Lanza el servidor Python en background
 * 2. Abre una ventana con el dashboard web
 * 3. Maneja el ciclo de vida de la aplicación
 */

const { app, BrowserWindow, ipcMain, dialog, Menu, Tray, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const log = require('electron-log');

// Configure logging
log.transports.file.level = 'info';
log.transports.file.maxSize = 10 * 1024 * 1024; // 10MB

// Global state
let mainWindow = null;
let pythonProcess = null;
let serverPort = null;
let isReady = false;

// Detect development mode
const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';

/**
 * Get resource path (works in production and development)
 */
function getResourcePath(...parts) {
    const basePath = isDev 
        ? path.join(__dirname, '..', '..')
        : path.join(process.resourcesPath, 'app.asar.unpacked');
    
    return path.join(basePath, ...parts);
}

/**
 * Get the Python launcher path
 */
function getLauncherPath() {
    if (isDev) {
        return path.join(__dirname, 'python', 'launcher.py');
    }
    // En producción, el launcher está en app.asar
    return path.join(__dirname, 'python', 'launcher.py');
}

/**
 * Get the project root directory (where main.py is located)
 */
function getProjectRoot() {
    if (isDev) {
        // desktop/src/ -> desktop/ -> raíz proyecto
        return path.join(__dirname, '..', '..');
    }
    // En producción: extraResources
    return process.resourcesPath;
}

/**
 * Log message with timestamp
 */
function logInfo(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] [INFO] ${message}`);
    log.info(message);
}

function logError(message) {
    const timestamp = new Date().toISOString();
    console.error(`[${timestamp}] [ERROR] ${message}`);
    log.error(message);
}

/**
 * Send ready signal to renderer
 */
function notifyReady(port) {
    serverPort = port;
    isReady = true;
    if (mainWindow) {
        mainWindow.webContents.send('server-ready', port);
    }
}

/**
 * Send error to renderer
 */
function notifyError(message) {
    if (mainWindow) {
        mainWindow.webContents.send('server-error', message);
    }
}

/**
 * Send status update to renderer
 */
function notifyStatus(message) {
    if (mainWindow) {
        mainWindow.webContents.send('server-status', message);
    }
}

/**
 * Parse output from Python launcher
 */
function parseLauncherOutput(data) {
    const line = data.toString().trim();
    
    if (line.startsWith('READY:')) {
        const port = parseInt(line.substring(6), 10);
        notifyReady(port);
        return port;
    }
    
    if (line.startsWith('ERROR:')) {
        const message = line.substring(6);
        notifyError(message);
        logError(`Python error: ${message}`);
        return null;
    }
    
    if (line.startsWith('STATUS:')) {
        const message = line.substring(7);
        notifyStatus(message);
        return null;
    }
    
    // Log other output
    if (line && !line.startsWith('=')) {
        logInfo(`Python: ${line}`);
    }
    
    return null;
}

/**
 * Start the Python launcher
 */
function startPython() {
    return new Promise((resolve, reject) => {
        logInfo('Starting Python launcher...');
        
        let launcherPath = getLauncherPath();
        
        if (!fs.existsSync(launcherPath)) {
            // Try alternate path
            let altPath = path.join(__dirname, 'python', 'launcher.py');
            if (fs.existsSync(altPath)) {
                launcherPath = altPath;
            } else {
                reject(new Error(`Launcher not found: ${launcherPath}`));
                return;
            }
        }
        
        // Determine Python executable
        const pythonExe = process.platform === 'win32' ? 'python.exe' : 'python3';
        const pythonPath = process.platform === 'win32' 
            ? path.join(__dirname, '..', '..', 'venv', 'Scripts', 'python.exe')
            : path.join(__dirname, '..', '..', 'venv', 'bin', 'python3');
        
        // Use venv Python if exists, otherwise system Python
        let pythonExec = pythonPath;
        if (!fs.existsSync(pythonExec)) {
            pythonExec = process.platform === 'win32' ? 'python' : 'python3';
            logInfo('Using system Python');
        } else {
            logInfo('Using bundled Python');
        }
        
        const env = { ...process.env };
        env.SRT2WEB_PROJECT_ROOT = getProjectRoot();
        
        pythonProcess = spawn(pythonExec, [launcherPath], {
            env,
            cwd: getProjectRoot(),
            stdio: ['pipe', 'pipe', 'pipe']
        });
        
        let buffer = '';
        
        pythonProcess.stdout.on('data', (data) => {
            buffer += data.toString();
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                const port = parseLauncherOutput(line);
                if (port) {
                    resolve(port);
                }
            }
        });
        
        pythonProcess.stderr.on('data', (data) => {
            logInfo(`Python stderr: ${data.toString().trim()}`);
        });
        
        pythonProcess.on('error', (err) => {
            logError(`Python process error: ${err.message}`);
            reject(err);
        });
        
        pythonProcess.on('exit', (code) => {
            logInfo(`Python process exited with code ${code}`);
            if (code !== 0 && code !== null) {
                notifyError(`Process exited with code ${code}`);
            }
        });
        
        // Timeout after 60 seconds
        setTimeout(() => {
            if (!isReady) {
                reject(new Error('Timeout waiting for Python launcher'));
            }
        }, 60000);
    });
}

/**
 * Create the main application window
 */
function createWindow() {
    logInfo('Creating main window...');
    
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        title: 'SRT2Web',
        icon: path.join(__dirname, '..', 'build', 'icon.png'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            spellcheck: false,
            webviewTag: false
        },
        show: false,
        backgroundColor: '#1a1a2e'
    });
    
    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        logInfo('Window shown');
    });
    
    // Handle window close
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
    
    // Create application menu
    createMenu();
    
    return mainWindow;
}

/**
 * Create application menu
 */
function createMenu() {
    const template = [
        {
            label: 'File',
            submenu: [
                {
                    label: 'Open Config File',
                    click: async () => {
                        const result = await dialog.showOpenDialog(mainWindow, {
                            title: 'Open Configuration',
                            filters: [{ name: 'YAML', extensions: ['yaml', 'yml'] }],
                            properties: ['openFile']
                        });
                        
                        if (!result.canceled && result.filePaths.length > 0) {
                            mainWindow.webContents.send('open-config', result.filePaths[0]);
                        }
                    }
                },
                { type: 'separator' },
                {
                    label: 'Exit',
                    accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
                    click: () => app.quit()
                }
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: 'Help',
            submenu: [
                {
                    label: 'Documentation',
                    click: () => {
                        require('electron').shell.openExternal('https://github.com/BrunoJimenez73/srt2web#readme');
                    }
                },
                {
                    label: 'View Logs',
                    click: () => {
                        const logPath = log.transports.file.getFile().path;
                        require('electron').shell.showItemInFolder(logPath);
                    }
                }
            ]
        }
    ];
    
    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

/**
 * Load the dashboard URL
 */
async function loadDashboard(port) {
    if (!mainWindow) {
        logError('Main window not created');
        return;
    }
    
    const url = `http://localhost:${port}`;
    logInfo(`Loading dashboard: ${url}`);
    
    try {
        await mainWindow.loadURL(url);
        logInfo('Dashboard loaded');
    } catch (err) {
        logError(`Failed to load dashboard: ${err.message}`);
        notifyError(`Failed to load dashboard: ${err.message}`);
    }
}

/**
 * Stop Python process
 */
function stopPython() {
    if (pythonProcess) {
        logInfo('Stopping Python process...');
        
        try {
            if (process.platform === 'win32') {
                spawn('taskkill', ['/pid', pythonProcess.pid.toString(), '/f', '/t']);
            } else {
                pythonProcess.kill('SIGTERM');
            }
        } catch (err) {
            logError(`Error stopping Python: ${err.message}`);
        }
        
        pythonProcess = null;
    }
}

/**
 * Application ready
 */
app.whenReady().then(async () => {
    logInfo('Application ready');
    
    try {
        // Create window
        createWindow();
        
        // Start Python
        const port = await startPython();
        
        // Load dashboard
        await loadDashboard(port);
        
        logInfo('Application started successfully');
    } catch (err) {
        logError(`Startup failed: ${err.message}`);
        dialog.showErrorBox('Startup Error', err.message);
        app.quit();
    }
});

/**
 * Handle activation (macOS)
 */
app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

/**
 * Handle all windows closed
 */
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

/**
 * Cleanup before quit
 */
app.on('before-quit', () => {
    logInfo('Application quitting...');
    stopPython();
});

/**
 * IPC Handlers
 */
ipcMain.handle('get-server-port', () => serverPort);

ipcMain.handle('restart-server', async () => {
    logInfo('Restarting server...');
    stopPython();
    await new Promise(r => setTimeout(r, 1000));
    
    try {
        const port = await startPython();
        await loadDashboard(port);
        return { success: true, port };
    } catch (err) {
        return { success: false, error: err.message };
    }
});

ipcMain.handle('stop-server', () => {
    stopPython();
    return { success: true };
});

ipcMain.handle('get-app-version', () => {
    return require(path.join(__dirname, '..', 'package.json')).version;
});

ipcMain.handle('open-external', (event, url) => {
    require('electron').shell.openExternal(url);
});

ipcMain.handle('show-item-in-folder', (event, filePath) => {
    require('electron').shell.showItemInFolder(filePath);
});