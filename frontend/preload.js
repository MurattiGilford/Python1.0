const { contextBridge, ipcRenderer } = require('electron');

// ============================================================================
// IPC BRIDGE - Secure communication between frontend and Electron
// ============================================================================

contextBridge.exposeInMainWorld('qai', {
  // Backend control
  backend: {
    checkHealth: () => ipcRenderer.invoke('backend:health'),
    restart: () => ipcRenderer.invoke('backend:restart')
  },

  // System information
  system: {
    getInfo: () => ipcRenderer.invoke('system:info'),
    getPlatform: () => process.platform,
    getVersion: () => process.versions.electron
  },

  // App paths
  paths: {
    get: (name) => ipcRenderer.invoke('app:getPath', name)
  }
});

// Log bridge readiness
console.log('✅ IPC Bridge ready - qai.backend, qai.system, qai.paths available');
