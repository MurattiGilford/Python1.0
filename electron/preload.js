const { contextBridge, ipcRenderer } = require('electron');
const { version } = require('./package.json');

contextBridge.exposeInMainWorld('RouteMindDesktop', {
  version,
  platform: process.platform,
  ping: () => ipcRenderer.invoke('ping')
});
