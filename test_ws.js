// Quick WebSocket test using Node.js WebSocket API
import WebSocket from 'ws';

const ws = new WebSocket('ws://localhost:8000/ws/checkins/');

ws.on('open', function open() {
  console.log('✓ Connected to WebSocket server');
});

ws.on('message', function message(data) {
  console.log('✓ Received message:', data.toString());
  const parsed = JSON.parse(data.toString());
  console.log('  Type:', parsed.type);
  console.log('  Message:', parsed.message || parsed.data);
});

ws.on('error', function error(err) {
  console.log('✗ WebSocket error:', err.message);
});

ws.on('close', function close() {
  console.log('Connection closed');
  process.exit(0);
});

// Close after 3 seconds
setTimeout(() => {
  console.log('\nClosing connection...');
  ws.close();
}, 3000);
