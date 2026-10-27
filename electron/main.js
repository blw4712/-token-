const { app, BrowserWindow, Menu, Tray, dialog, ipcMain, nativeImage, screen } = require('electron')
const { spawn } = require('child_process')
const fs = require('fs')
const os = require('os')
const path = require('path')

const ROOT = path.join(__dirname, '..')
const PET_SIZE = { width: 236, height: 146 }
const DEV_URL = process.env.ELECTRON_DEV_URL || ''

let backend = null
let panel = null
let pet = null
let tray = null
let baseUrl = ''
let quitting = false

// 面板没有动画和 3D 内容，关掉硬件加速可以避开部分显卡驱动的启动崩溃。
app.disableHardwareAcceleration()

// 用户数据统一放到数据目录，避免漫游目录权限导致单实例锁创建失败。
function dataDir() {
  return process.env.AGENT_CONSOLE_DATA || path.join(os.homedir(), '.agent-console')
}

app.setPath('userData', path.join(dataDir(), 'electron'))

function serverFile() {
  return process.env.AGENT_CONSOLE_SERVER || path.join(os.homedir(), '.agent-console', 'server.json')
}

function readServer() {
  try {
    return JSON.parse(fs.readFileSync(serverFile(), 'utf8'))
  } catch {
    return null
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function healthy(url) {
  try {
    const response = await fetch(`${url}/api/health`, { signal: AbortSignal.timeout(1500) })
    return response.ok
  } catch {
    return false
  }
}

function startBackend(port) {
  const python = process.env.AGENT_CONSOLE_PYTHON || 'python'
  const args = [path.join(ROOT, 'backend', 'run.py')]
  if (port) args.push('--port', String(port))
  backend = spawn(python, args, {
    cwd: ROOT,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    windowsHide: true,
    stdio: 'ignore'
  })
  backend.on('error', () => {
    backend = null
  })
}

async function ensureBackend() {
  const existing = readServer()
  if (existing && existing.url && (await healthy(existing.url))) {
    return existing.url
  }

  if (DEV_URL) {
    const devBase = 'http://127.0.0.1:8765'
    if (!(await healthy(devBase))) startBackend(8765)
    else return devBase
  } else {
    startBackend(0)
  }

  for (let index = 0; index < 60; index += 1) {
    await sleep(400)
    const info = readServer()
    if (info && info.url && (await healthy(info.url))) return info.url
  }
  throw new Error('后端接口启动超时，请确认已安装 fastapi 与 uvicorn。')
}

function panelUrl() {
  return DEV_URL || `${baseUrl}/`
}

function createPanel() {
  panel = new BrowserWindow({
    width: 1180,
    height: 800,
    minWidth: 960,
    minHeight: 620,
    backgroundColor: '#080c11',
    title: 'Agent Console',
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  panel.loadURL(panelUrl())
  panel.once('ready-to-show', () => panel.show())
  panel.on('close', (event) => {
    if (!quitting) {
      event.preventDefault()
      panel.hide()
    }
  })
}

function petPosition() {
  const { workArea } = screen.getPrimaryDisplay()
  return {
    x: Math.round(workArea.x + workArea.width - PET_SIZE.width - 18),
    y: Math.round(workArea.y + workArea.height - PET_SIZE.height - 18)
  }
}

function createPet() {
  const position = petPosition()
  pet = new BrowserWindow({
    ...PET_SIZE,
    x: position.x,
    y: position.y,
    frame: false,
    transparent: true,
    resizable: false,
    maximizable: false,
    minimizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  pet.loadURL(`${baseUrl}/pet.html`)
  pet.once('ready-to-show', () => pet.showInactive())
  pet.on('close', (event) => {
    if (!quitting) {
      event.preventDefault()
      pet.hide()
    }
  })
}

function showPanel() {
  if (!panel) return
  if (panel.isMinimized()) panel.restore()
  panel.show()
  panel.focus()
}

async function rescan() {
  if (!baseUrl) return
  try {
    await fetch(`${baseUrl}/api/scan?full=false`, { method: 'POST' })
    if (panel && !panel.isDestroyed()) panel.webContents.send('scan-done')
    if (pet && !pet.isDestroyed()) pet.webContents.reload()
  } catch (error) {
    dialog.showErrorBox('重新扫描失败', String(error.message || error))
  }
}

function togglePet() {
  if (!pet) return
  if (pet.isVisible()) pet.hide()
  else pet.showInactive()
  buildTray()
}

function buildTray() {
  const visible = pet ? pet.isVisible() : false
  const menu = Menu.buildFromTemplate([
    { label: '打开面板', click: showPanel },
    { label: '重新扫描', click: rescan },
    { label: visible ? '隐藏桌宠' : '显示桌宠', click: togglePet },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        quitting = true
        if (backend) backend.kill()
        app.quit()
      }
    }
  ])
  tray.setContextMenu(menu)
}

function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'tray.png')
  const icon = nativeImage.createFromPath(iconPath)
  tray = new Tray(icon.isEmpty() ? nativeImage.createEmpty() : icon)
  tray.setToolTip('Agent Console')
  tray.on('double-click', showPanel)
  buildTray()
}

ipcMain.handle('open-panel', () => {
  showPanel()
})

ipcMain.handle('hide-pet', () => {
  if (pet) pet.hide()
  buildTray()
})

ipcMain.handle('scan', async () => {
  if (!baseUrl) return { ok: false }
  await rescan()
  return { ok: true }
})

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', showPanel)

  app.on('before-quit', () => {
    quitting = true
    if (backend) backend.kill()
  })

  app.whenReady().then(async () => {
    try {
      baseUrl = await ensureBackend()
    } catch (error) {
      dialog.showErrorBox('Agent Console 启动失败', String(error.message || error))
      quitting = true
      app.quit()
      return
    }

    createPanel()
    createPet()
    createTray()
  })

  app.on('window-all-closed', () => {
    // 常驻托盘，等用户从菜单退出。
  })
}
