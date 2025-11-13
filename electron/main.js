const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

const SERVER_URL = process.env.ROUTEMIND_SERVER_URL || 'http://127.0.0.1:5000';
const PYTHON_EXECUTABLE = process.env.ROUTEMIND_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
let pythonProcess;

function createPythonProcess() {
  const scriptPath = path.join(__dirname, '..', 'app.py');
  const workingDirectory = path.join(__dirname, '..');

  pythonProcess = spawn(PYTHON_EXECUTABLE, [scriptPath], {
    cwd: workingDirectory,
    env: {
      ...process.env,
      FLASK_ENV: 'production',
      FLASK_RUN_PORT: '5000',
      FLASK_RUN_HOST: '127.0.0.1'
    },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[python] ${data}`.trim());
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[python] ${data}`.trim());
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`Python process exited with code ${code ?? 'unknown'}${signal ? ` (signal ${signal})` : ''}`);
    pythonProcess = undefined;
    if (!app.isQuiting) {
      app.quit();
    }
  });
}

function waitForServer(url, retries = 120, interval = 250) {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const timer = setInterval(() => {
      attempts += 1;
      const request = http.get(url, (response) => {
        response.resume();
        clearInterval(timer);
        resolve();
      });

      request.on('error', (error) => {
        if (attempts >= retries) {
          clearInterval(timer);
          reject(error);
        }
      });
    }, interval);
  });
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 832,
    minWidth: 1024,
    minHeight: 720,
    title: 'RouteMind Control Centre',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  try {
    await waitForServer(SERVER_URL);
    await window.loadURL(SERVER_URL);
  } catch (error) {
    window.loadURL('data:text/plain,Unable%20to%20connect%20to%20the%20RouteMind%20server.');
    console.error('Failed to reach RouteMind Flask server:', error);
  }
}


ipcMain.handle('ping', () => 'pong');

app.whenReady().then(() => {
  createPythonProcess();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('before-quit', () => {
  app.isQuiting = true;
  if (pythonProcess) {
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t']);
    } else {
      pythonProcess.kill('SIGINT');
    }
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
