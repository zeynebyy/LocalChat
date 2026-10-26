const { app, BrowserWindow } = require('electron');
const path = require('path');
const { exec } = require('child_process');

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  win.loadFile('frontend/index.html');


  // Flask backend'i başlat (senin projen)
  const backend = exec('python backend/app.py');

  backend.stdout.on('data', data => console.log(`[BACKEND]: ${data}`));
  backend.stderr.on('data', err => console.error(`[BACKEND HATA]: ${err}`));
}

app.whenReady().then(createWindow);
