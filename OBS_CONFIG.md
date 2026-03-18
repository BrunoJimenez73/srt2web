# Configuración de OBS para SRT2Web

## Requisitos
- OBS Studio 28+ con soporte para SRT
- Conexión de red estable

## Configuración en OBS

### 1. Configurar Salida
- **Modo de salida**: Salida simple
- **Salida**: Habilitar "Usar codificación de hardware" si está disponible
- **Calidad de video**: Estándar o Alta calidad

### 2. Configurar Salida SRT
En el menú: **Herramientas → Salida virtual → Configuración**

O alternativamente, usar SRT como salida directa:
- Ir a **Archivo → Configuración → Salida**
- Modo de salida: **Simple**
- Salida: **SRT**
- Servidor: `srt://TU_IP:9000?mode=caller&latency=1000000`

### 3. Verificar Conexión
1. Inicia el servidor SRT2Web
2. Conecta OBS a la dirección SRT
3. Verifica que el pipeline esté recibiendo datos:
   - El servidor mostrará mensajes de segmentos generados
   - Deberías ver archivos `.ts` en `output/hls/`

## Solución de Problemas

### Si no se recibe video
1. Verifica que el firewall permita el puerto 9000
2. Asegúrate de usar la IP correcta del servidor
3. Verifica que OBS esté en modo "caller" con latency=1000000

### Calidad de video baja
1. En la configuración del encoder en el dashboard, ajusta:
   - **Calidad de Video**: `Slow` o `Slower` para mejor calidad
   - **Perfil de Video**: `High`
   - **CRF**: 16-18 para equilibrio calidad/velocidad

### Si el servidor no detecta GPU
1. Verifica drivers de GPU actualizados
2. En la configuración, usa `encoder_mode: cpu` para forzar codificación por CPU
3. Asegúrate de tener FFmpeg con soporte para tu GPU
