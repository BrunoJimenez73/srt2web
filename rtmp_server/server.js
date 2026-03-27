const NodeMediaServer = require('node-media-server');

const config = {
  rtmp: {
    port: 1935,
    chunk_size: 60000,
    gop_cache: true,
    ping: 30,
    ping_timeout: 60
  },
  http: {
    port: 8000,
    allow_origin: '*'
  },
  trans: {
    ffmpeg: 'ffmpeg',
    tasks: [
      {
        app: 'live',
        hls: true,
        hlsFlags: '[hls_time=2:hls_list_size=3:hls_flags=delete_segments]',
        dash: true,
        dashFlags: '[f=dash:window_size=3:extra_window_size=3]'
      }
    ]
  }
};

var nms = new NodeMediaServer(config);

nms.on('prePublish', (id, StreamPath, args) => {
  console.log('[NodeEvent] prePublish:', { id, StreamPath, args });
});

nms.on('postPublish', (id, StreamPath, args) => {
  console.log('[NodeEvent] postPublish:', { id, StreamPath, args });
});

nms.on('prePlay', (id, StreamPath, args) => {
  console.log('[NodeEvent] prePlay:', { id, StreamPath, args });
});

nms.on('postPlay', (id, StreamPath, args) => {
  console.log('[NodeEvent] postPlay:', { id, StreamPath, args });
});

console.log('===========================================');
console.log('  Node Media Server - RTMP Server');
console.log('  RTMP: rtmp://localhost:1935/live/STREAM');
console.log('  HTTP-FLV: http://localhost:8000/live/STREAM.flv');
console.log('===========================================');

nms.run();
