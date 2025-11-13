const { app, BrowserWindow, nativeImage, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let backendProcess = null;
let mainWindow = null;
const BACKEND_PORT = 7861;

// ============================================================================
// BACKEND AUTO-LAUNCH
// ============================================================================

function startBackend() {
  return new Promise((resolve, reject) => {
    console.log('🚀 Starting backend...');

    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    // FIXED: Changed from app_auto_orch.py to app.py
    const backendPath = path.join(__dirname, '..', 'backend', 'app.py');

    backendProcess = spawn(pythonCmd, [backendPath], {
      cwd: path.join(__dirname, '..', 'backend'),
      env: { ...process.env }
    });

    backendProcess.stdout.on('data', (data) => {
      console.log(`Backend: ${data.toString().trim()}`);
      if (data.toString().includes('Uvicorn running')) {
        resolve();
      }
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`Backend Error: ${data.toString().trim()}`);
    });

    backendProcess.on('error', (error) => {
      console.error('Failed to start backend:', error);
      reject(error);
    });

    backendProcess.on('close', (code) => {
      console.log(`Backend exited with code ${code}`);
      backendProcess = null;
    });

    // Timeout after 10 seconds
    setTimeout(() => resolve(), 10000);
  });
}

function checkBackendHealth() {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${BACKEND_PORT}/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(2000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function ensureBackend() {
  const isHealthy = await checkBackendHealth();
  if (!isHealthy) {
    await startBackend();
    await new Promise(resolve => setTimeout(resolve, 3000));
  }
}

// ============================================================================
// IPC HANDLERS
// ============================================================================

ipcMain.handle('backend:health', async () => {
  return await checkBackendHealth();
});

ipcMain.handle('backend:restart', async () => {
  if (backendProcess) {
    backendProcess.kill();
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  await startBackend();
  return { success: true };
});

ipcMain.handle('system:info', () => {
  return {
    platform: process.platform,
    arch: process.arch,
    version: app.getVersion(),
    electronVersion: process.versions.electron,
    nodeVersion: process.versions.node
  };
});

// ============================================================================
// WINDOW CREATION
// ============================================================================

const createWindow = () => {
  // Try to load icon, but don't fail if it doesn't exist
  let icon = null;
  try {
    const iconPath = path.join(__dirname, '..', 'assets', 'icon.ico');
    icon = nativeImage.createFromPath(iconPath);
  } catch (error) {
    console.log('Icon not found, using default');
  }

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    icon,
    title: 'Quantum AI Lab - Nuclear Spaceship',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    },
    backgroundColor: '#ffffff'
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // Open DevTools in development mode
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }
};

// ============================================================================
// APP LIFECYCLE
// ============================================================================

app.whenReady().then(async () => {
  console.log('⚡ Quantum AI Lab - Nuclear Spaceship starting...');

  try {
    await ensureBackend();
    console.log('✅ Backend ready');
  } catch (error) {
    console.error('❌ Backend failed:', error);
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (backendProcess) {
    console.log('Stopping backend...');
    backendProcess.kill();
  }

  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (backendProcess) backendProcess.kill();
});

console.log('⚡ Quantum AI Lab - Nuclear Spaceship Edition v5.1');
console.log('📡 Backend auto-starts on port', BACKEND_PORT);
