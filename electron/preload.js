const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('desktop', {
  openPanel: () => ipcRenderer.invoke('open-panel'),
  hidePet: () => ipcRenderer.invoke('hide-pet'),
  scan: () => ipcRenderer.invoke('scan'),
  onScanDone: (callback) => {
    ipcRenderer.on('scan-done', () => callback())
  }
})
