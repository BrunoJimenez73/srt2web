const { OBSWebSocket } = require('obs-websocket-js');

const obs = new OBSWebSocket();

obs.on('StreamStateChanged', (data) => {
  console.log('StreamStateChanged:', JSON.stringify(data));
});

async function check() {
  try {
    await obs.connect('ws://localhost:4455', '123456', { rpcVersion: 1 });
    
    const status = await obs.call('GetStreamStatus');
    console.log('Stream status:', status);
    
    await obs.disconnect();
  } catch (e) {
    console.error('Error:', e.message);
  }
}

check();
