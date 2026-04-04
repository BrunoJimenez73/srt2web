"""
Async Pipeline v2 - Pipeline asíncrono mejorado con asyncio.

Esta versión utiliza asyncio para procesamiento asíncrono completo,
reemplazando threading por un modelo más eficiente y escalable.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from core.types import ModuleState, PipelineData, PipelineStatus, PipelineState, ModuleStatus
from core.exceptions import PipelineError, PipelineStateError, ModuleProcessingError

logger = logging.getLogger("srt2web.async_pipeline_v2")


class AsyncPipelineV2:
    """
    Pipeline asíncrono mejorado con asyncio.
    
    Características:
    - Procesamiento asíncrono completo (sin threading)
    - Soporte para módulos que implementan ProcessingModule
    - Manejo de errores mejorado con reintentos
    - Métricas de rendimiento por módulo
    - Cancelación graceful
    """
    
    def __init__(
        self,
        max_concurrent_chunks: int = 3,
        retry_attempts: int = 2,
        retry_delay: float = 1.0,
    ):
        """
        Inicializar pipeline asíncrono.
        
        Args:
            max_concurrent_chunks: Máximo de chunks procesando simultáneamente
            retry_attempts: Número de reintentos ante fallos
            retry_delay: Retraso entre reintentos (segundos)
        """
        self.max_concurrent_chunks = max_concurrent_chunks
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Estado del pipeline
        self._state = PipelineState.IDLE
        self._status = PipelineStatus()
        self._start_time: Optional[float] = None
        
        # Módulos y componentes
        self._modules: List[Any] = []  # ProcessingModule implementations
        self._input_source: Optional[Any] = None
        self._output_sink: Optional[Any] = None
        
        # Control de concurrencia
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        
        # Callbacks
        self._on_log: Optional[Callable[[str, str], None]] = None
        self._on_state_change: Optional[Callable[[str], None]] = None
        self._on_chunk_complete: Optional[Callable[[int, PipelineData], None]] = None
        
        # Métricas
        self._chunks_processed = 0
        self._chunks_failed = 0
        self._total_processing_time = 0.0
    
    @property
    def state(self) -> PipelineState:
        """Obtener estado actual del pipeline."""
        return self._state
    
    @property
    def status(self) -> PipelineStatus:
        """Obtener estado completo del pipeline."""
        return self._status
    
    @property
    def is_running(self) -> bool:
        """Verificar si el pipeline está corriendo."""
        return self._state in [PipelineState.RUNNING, PipelineState.STARTING]
    
    def set_input_source(self, source: Any) -> None:
        """Establecer fuente de entrada."""
        self._input_source = source
    
    def set_output_sink(self, sink: Any) -> None:
        """Establecer destino de salida."""
        self._output_sink = sink
    
    def register_module(self, module: Any) -> None:
        """
        Registrar un módulo en el pipeline.
        
        El módulo debe implementar la interfaz ProcessingModule:
        - initialize() -> None
        - process(data: PipelineData) -> PipelineData
        - shutdown() -> None
        - get_status() -> ModuleStatus
        """
        self._modules.append(module)
    
    def _set_state(self, state: PipelineState) -> None:
        """Cambiar estado del pipeline."""
        self._state = state
        self._status.state = state
        
        if self._on_state_change:
            try:
                self._on_state_change(state.value)
            except Exception as e:
                logger.error(f"Error en callback de estado: {e}")
        
        logger.info(f"Pipeline state changed to: {state.value}")
    
    async def initialize(self) -> None:
        """
        Inicializar el pipeline y todos sus módulos.
        
        Este método debe llamarse antes de iniciar el procesamiento.
        """
        logger.info("Initializing async pipeline v2...")
        self._set_state(PipelineState.STARTING)
        
        try:
            # Inicializar semáforo para concurrencia
            self._semaphore = asyncio.Semaphore(self.max_concurrent_chunks)
            
            # Inicializar módulos secuencialmente
            for module in self._modules:
                try:
                    if asyncio.iscoroutinefunction(module.initialize):
                        await module.initialize()
                    else:
                        module.initialize()
                    logger.info(f"Module '{module.name}' initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize module '{module.name}': {e}")
                    raise
            
            # Inicializar input/output si existen
            if self._input_source and hasattr(self._input_source, 'initialize'):
                if asyncio.iscoroutinefunction(self._input_source.initialize):
                    await self._input_source.initialize()
            
            if self._output_sink and hasattr(self._output_sink, 'initialize'):
                if asyncio.iscoroutinefunction(self._output_sink.initialize):
                    await self._output_sink.initialize()
            
            self._start_time = time.time()
            self._set_state(PipelineState.IDLE)  # Volver a IDLE después de inicializar
            logger.info("Async pipeline v2 initialized successfully")
            
        except Exception as e:
            self._set_state(PipelineState.ERROR)
            logger.error(f"Pipeline initialization failed: {e}")
            raise
    
    async def start(self) -> None:
        """
        Iniciar procesamiento del pipeline.
        
        Este método lanza las tareas asíncronas y retorna inmediatamente.
        """
        if self._state != PipelineState.IDLE:
            raise PipelineStateError(f"Cannot start pipeline in state: {self._state.value}")
        
        logger.info("Starting async pipeline v2...")
        self._set_state(PipelineState.STARTING)
        self._stop_event.clear()
        
        # Crear tarea principal de procesamiento
        main_task = asyncio.create_task(self._process_loop())
        self._tasks.append(main_task)
        
        self._set_state(PipelineState.RUNNING)
        logger.info("Async pipeline v2 started")
    
    async def _process_loop(self) -> None:
        """Bucle principal de procesamiento."""
        logger.info("Process loop started")
        
        try:
            while not self._stop_event.is_set():
                # Obtener datos del input
                data = await self._get_input_data()
                if data is None:
                    await asyncio.sleep(0.01)  # Pequeña pausa si no hay data
                    continue
                
                # Procesar chunk
                task = asyncio.create_task(self._process_chunk(data))
                self._tasks.append(task)
                
        except asyncio.CancelledError:
            logger.info("Process loop cancelled")
        except Exception as e:
            logger.error(f"Process loop error: {e}")
            self._set_state(PipelineState.ERROR)
        
        logger.info("Process loop ended")
    
    async def _get_input_data(self) -> Optional[PipelineData]:
        """Obtener datos de entrada (implementar según input source)."""
        if self._input_source is None:
            return None
        
        try:
            if hasattr(self._input_source, 'get_data'):
                if asyncio.iscoroutinefunction(self._input_source.get_data):
                    return await self._input_source.get_data()
                else:
                    return self._input_source.get_data()
        except Exception as e:
            logger.error(f"Error getting input data: {e}")
        
        return None
    
    async def _process_chunk(self, data: PipelineData) -> PipelineData:
        """
        Procesar un chunk a través del pipeline.
        
        Args:
            data: Datos del chunk a procesar
            
        Returns:
            Datos procesados
        """
        async with self._semaphore:  # Limitar concurrencia
            chunk_start = time.time()
            chunk_index = data.chunk_index
            
            try:
                # Procesar a través de cada módulo
                for module in self._modules:
                    if self._stop_event.is_set():
                        logger.info(f"Processing stopped for chunk {chunk_index}")
                        break
                    
                    data = await self._process_with_retry(module, data)
                
                # Enviar a output
                if self._output_sink and data:
                    await self._send_to_output(data)
                
                # Actualizar métricas
                processing_time = time.time() - chunk_start
                self._chunks_processed += 1
                self._total_processing_time += processing_time
                
                if self._on_chunk_complete:
                    self._on_chunk_complete(chunk_index, data)
                
                logger.debug(f"Chunk {chunk_index} processed in {processing_time:.2f}s")
                return data
                
            except Exception as e:
                self._chunks_failed += 1
                logger.error(f"Error processing chunk {chunk_index}: {e}")
                raise
    
    async def _process_with_retry(
        self, 
        module: Any, 
        data: PipelineData
    ) -> PipelineData:
        """
        Procesar datos con módulo, reintentando ante fallos.
        
        Args:
            module: Módulo procesador
            data: Datos a procesar
            
        Returns:
            Datos procesados
        """
        last_error = None
        
        for attempt in range(self.retry_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(module.process):
                    return await module.process(data)
                else:
                    return module.process(data)
                    
            except Exception as e:
                last_error = e
                if attempt < self.retry_attempts:
                    logger.warning(
                        f"Module '{module.name}' failed (attempt {attempt + 1}/{self.retry_attempts + 1}): {e}"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Backoff
                else:
                    break
        
        raise ModuleProcessingError(
            f"Module '{module.name}' failed after {self.retry_attempts + 1} attempts",
            module=module.name,
            context={"last_error": str(last_error)}
        )
    
    async def _send_to_output(self, data: PipelineData) -> None:
        """Enviar datos procesados al output."""
        if self._output_sink is None:
            return
        
        try:
            if hasattr(self._output_sink, 'write'):
                if asyncio.iscoroutinefunction(self._output_sink.write):
                    await self._output_sink.write(data)
                else:
                    self._output_sink.write(data)
        except Exception as e:
            logger.error(f"Error sending to output: {e}")
    
    async def stop(self) -> None:
        """
        Detener el pipeline gracefulamente.
        
        Espera a que los chunks en procesamiento terminen.
        """
        if not self.is_running:
            return
        
        logger.info("Stopping async pipeline v2...")
        self._set_state(PipelineState.STOPPING)
        self._stop_event.set()
        
        # Esperar tareas pendientes (timeout: 30s)
        if self._tasks:
            done, pending = await asyncio.wait(
                self._tasks, 
                timeout=30.0,
                return_when=asyncio.FIRST_EXCEPTION
            )
            
            # Cancelar tareas pendientes
            for task in pending:
                task.cancel()
            
            self._tasks.clear()
        
        self._set_state(PipelineState.IDLE)
        logger.info("Async pipeline v2 stopped")
    
    async def shutdown(self) -> None:
        """
        Cerrar y liberar recursos del pipeline.
        
        Detiene el procesamiento y cierra todos los módulos.
        """
        await self.stop()
        
        logger.info("Shutting down async pipeline v2...")
        
        # Cerrar módulos
        for module in self._modules:
            try:
                if asyncio.iscoroutinefunction(module.shutdown):
                    await module.shutdown()
                else:
                    module.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down module '{module.name}': {e}")
        
        # Cerrar input/output
        if self._input_source and hasattr(self._input_source, 'shutdown'):
            try:
                if asyncio.iscoroutinefunction(self._input_source.shutdown):
                    await self._input_source.shutdown()
                else:
                    self._input_source.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down input: {e}")
        
        if self._output_sink and hasattr(self._output_sink, 'shutdown'):
            try:
                if asyncio.iscoroutinefunction(self._output_sink.shutdown):
                    await self._output_sink.shutdown()
                else:
                    self._output_sink.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down output: {e}")
        
        logger.info("Async pipeline v2 shutdown complete")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtener métricas del pipeline.
        
        Returns:
            Diccionario con métricas de rendimiento
        """
        uptime = time.time() - self._start_time if self._start_time else 0
        avg_time = (
            self._total_processing_time / self._chunks_processed 
            if self._chunks_processed > 0 else 0
        )
        
        return {
            "state": self._state.value,
            "chunks_processed": self._chunks_processed,
            "chunks_failed": self._chunks_failed,
            "uptime_seconds": uptime,
            "avg_processing_time": avg_time,
            "modules_count": len(self._modules),
            "max_concurrent": self.max_concurrent_chunks,
        }
    
    def set_log_callback(self, callback: Callable[[str, str], None]) -> None:
        """Establecer callback para logs."""
        self._on_log = callback
    
    def set_state_callback(self, callback: Callable[[str], None]) -> None:
        """Establecer callback para cambios de estado."""
        self._on_state_change = callback
    
    def set_chunk_complete_callback(
        self, 
        callback: Callable[[int, PipelineData], None]
    ) -> None:
        """Establecer callback para chunk completado."""
        self._on_chunk_complete = callback