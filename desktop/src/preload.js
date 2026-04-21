/**
 * SRT2Web Desktop - Preload Script
 * 
 * Expone APIs seguras al renderer via contextBridge.
 * El renderer NO puede acceder directamente a Node.js.
 */

const { contextBridge, ipcRenderer } = require('electron');

// APIs expuestas al renderer
contextBridge.exposeInMainWorld('srt2web', {
    /**
     * Get the server port
     */
    getServerPort: () => ipcRenderer.invoke('get-server-port'),
    
    /**
     * Restart the server
     */
    restartServer: () => ipcRenderer.invoke('restart-server'),
    
    /**
     * Stop the server
     */
    stopServer: () => ipcRenderer.invoke('stop-server'),
    
    /**
     * Get app version
     */
    getVersion: () => ipcRenderer.invoke('get-app-version'),
    
    /**
     * Open external URL
     */
    openExternal: (url) => ipcRenderer.invoke('open-external', url),
    
    /**
     * Show item in folder
     */
    showItemInFolder: (path) => ipcRenderer.invoke('show-item-in-folder', path),
    
    /**
     * Listen for server ready events
     */
    onServerReady: (callback) => {
        ipcRenderer.on('server-ready', (event, port) => callback(port));
    },
    
    /**
     * Listen for server error events
     */
    onServerError: (callback) => {
        ipcRenderer.on('server-error', (event, message) => callback(message));
    },
    
    /**
     * Listen for server status updates
     */
    onServerStatus: (callback) => {
        ipcRenderer.on('server-status', (event, message) => callback(message));
    },
    
    /**
     * Listen for config file open requests
     */
    onOpenConfig: (callback) => {
        ipcRenderer.on('open-config', (event, path) => callback(path));
    },
    
    /**
     * Remove all listeners for an event
     */
    removeAllListeners: (channel) => {
        ipcRenderer.removeAllListeners(channel);
    }
});

// Platform info
contextBridge.exposeInMainWorld('platform', {
    os: process.platform,
    arch: process.arch,
    isWindows: process.platform === 'win32',
    isMac: process.platform === 'darwin',
    isLinux: process.platform === 'linux'
});

// Console message for debugging
console.log('[SRT2Web] Preload script loaded');