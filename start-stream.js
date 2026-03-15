const { OBSWebSocket } = require('obs-websocket-js');

async function startStream() {
  const obs = new OBSWebSocket();
  
  try {
    await obs.connect('ws://localhost:4455', '123456', { rpcVersion: 1 });
    console.log('Conectado a OBS!');
    
    const status = await obs.call('GetStreamStatus');
    console.log('Stream activo:', status.outputActive);
    
    if (!status.outputActive) {
      console.log('Iniciando stream...');
      await obs.call('StartStream');
    }
    
    await obs.disconnect();
  } catch (e) {
    console.error('Error:', e.message || e);
  }
}

startStream();
