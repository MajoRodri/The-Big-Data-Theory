/* global Terminal, FitAddon, io */

const term = new Terminal({
  cursorBlink: true,
  fontFamily: '"Cascadia Code", Consolas, "Liberation Mono", monospace',
  fontSize: 14,
  lineHeight: 1.2,
  theme: {
    background: '#071017',
    foreground: '#edf7fb',
    cursor: '#55d6d2',
    black: '#071017',
    red: '#ff6b6b',
    green: '#73d99f',
    yellow: '#f3c969',
    blue: '#6aa6ff',
    magenta: '#d98cff',
    cyan: '#55d6d2',
    white: '#edf7fb',
    brightBlack: '#5f7482',
    brightRed: '#ff8f8f',
    brightGreen: '#98edba',
    brightYellow: '#ffe199',
    brightBlue: '#9ec4ff',
    brightMagenta: '#e7b5ff',
    brightCyan: '#8ff1ed',
    brightWhite: '#ffffff'
  }
});
const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);
term.open(document.getElementById('terminal'));
fitAddon.fit();
const socket = io();
socket.on('output', (data) => term.write(data));
socket.on('exit', () => term.write('\r\n[Sesión finalizada]\r\n'));
term.onData((data) => socket.emit('input', data));
window.addEventListener('resize', () => {
  fitAddon.fit();
  socket.emit('resize', { rows: term.rows, cols: term.cols });
});
socket.on('connect', () => {
  fitAddon.fit();
  socket.emit('resize', { rows: term.rows, cols: term.cols });
});
