// main.js
const { app, BrowserWindow } = require('electron');
const { exec } = require('child_process');
const path = require('path');

// Function to start the Flask server
function startFlask() {
    exec('python ./idf_tool/app.py', (error, stdout, stderr) => {
        if (error) {
            console.error(`Error starting Flask: ${error}`);
            return;
        }
        console.log(`Flask stdout: ${stdout}`);
        console.error(`Flask stderr: ${stderr}`);
    });
}

// Create the main Electron window
function createWindow() {
    const win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
        },
    });

    // Load the Flask app at localhost
    win.loadURL('http://127.0.0.1:5000');
}

app.whenReady().then(() => {
    startFlask();
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});
