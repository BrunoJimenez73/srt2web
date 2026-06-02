"""
Benchmark reproducible para el pipeline SRT2Web.

Ejecuta el pipeline con un video corto y mide tiempos por etapa.
Genera resultados en JSON para comparar optimizaciones futuras.

Uso:
    python tests/benchmark/benchmark_pipeline.py
    python tests/benchmark/benchmark_pipeline.py --video tests/resources/short_video.mp4
    python tests/benchmark/benchmark_pipeline.py --mode sequential --chunks 5
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Asegurar que el proyecto está en el path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import ConfigManager
from core.unified_pipeline import PipelineMode, UnifiedPipeline
from modules.inputs.file_input import FileInput
from modules.outputs.hls_output import HLSOutput

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("benchmark")


def create_dummy_video(output_path: Path, duration: int = 10) -> None:
    """Crear un video dummy corto para benchmark si no existe."""
    import subprocess

    if output_path.exists():
        logger.info(f"Video ya existe: {output_path}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Crear video negro con audio silencioso usando FFmpeg
    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size=640x360:rate=30",
        "-f",
        "lavfi",
        "-i",
        f"anoisesrc=d={duration}:c=pink:r=44100",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        "-y",
        str(output_path),
    ]

    logger.info(f"Creando video dummy: {output_path}")
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        logger.info(f"Video creado: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error creando video: {e.stderr.decode()}")
        raise
    except FileNotFoundError:
        logger.error("FFmpeg no encontrado. Instale FFmpeg primero.")
        raise


def run_benchmark(
    video_path: str,
    mode: str = "thread_parallel",
    max_concurrent: int = 2,
    num_chunks: int = 3,
) -> dict:
    """
    Ejecutar benchmark del pipeline.

    Args:
        video_path: Ruta al video de prueba
        mode: Modo de ejecucion (sequential, thread_parallel, asyncio)
        max_concurrent: Max chunks concurrentes (para modos paralelos)
        num_chunks: Numero de chunks a procesar

    Returns:
        Dict con resultados del benchmark
    """
    logger.info(f"Iniciando benchmark: mode={mode}, chunks={num_chunks}")

    # Cargar configuracion base
    config_manager = ConfigManager()
    config = config_manager.load_config()

    # Modificar config para benchmark
    config.modules.transcriber.model = "tiny"  # Modelo rapido para benchmark
    config.pipeline.chunk_duration_sec = 5
    config.output.web.segment_duration = 5

    # Crear pipeline
    pipeline_mode = PipelineMode(mode)
    pipeline = UnifiedPipeline(
        mode=pipeline_mode,
        max_concurrent_chunks=max_concurrent,
        buffer_size=5,
    )

    # Configurar input de archivo
    file_input = FileInput()
    file_input.configure({"file_path": video_path, "chunk_duration_sec": 5})
    pipeline.set_input_source(file_input)

    # Configurar output HLS temporal
    hls_output = HLSOutput()
    hls_output.configure(
        {
            "output_dir": str(PROJECT_ROOT / "temp_benchmark_hls"),
            "segment_duration": 5,
            "list_size": 3,
        }
    )
    pipeline.set_output_sink(hls_output)

    # Registrar módulos y inicializar
    pipeline.register_module(file_input)

    # Métricas de seguimiento
    results = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "max_concurrent": max_concurrent,
        "video_path": video_path,
        "config": {
            "model": config.modules.transcriber.model,
            "chunk_duration": config.pipeline.chunk_duration_sec,
        },
        "chunks_processed": 0,
        "total_time_sec": 0,
        "avg_chunk_time_ms": 0,
        "stages": {},
        "errors": [],
    }

    # Parche para limitar chunks procesados
    original_process = pipeline._process_chunk_sync if hasattr(pipeline, "_process_chunk_sync") else None
    chunks_processed = [0]

    def limit_chunks(*args, **kwargs):
        if chunks_processed[0] >= num_chunks:
            asyncio.run(pipeline.stop())
            return None
        chunks_processed[0] += 1
        if original_process:
            return original_process(*args, **kwargs)
        return None

    # Ejecutar benchmark
    start_time = time.perf_counter()
    try:
        pipeline.start()
        # Esperar a que termine o se detenga
        while pipeline.get_status()["state"] == "running":
            time.sleep(0.5)
            if chunks_processed[0] >= num_chunks:
                break
        asyncio.run(pipeline.stop())
    except Exception as e:
        results["errors"].append(str(e))
        logger.error(f"Error en benchmark: {e}")
    finally:
        total_time = time.perf_counter() - start_time
        results["total_time_sec"] = total_time
        results["chunks_processed"] = chunks_processed[0]

        # Obtener métricas del pipeline
        status = pipeline.get_status()
        if "metrics" in status:
            results["avg_chunk_time_ms"] = status["metrics"].get("avg_processing_time_ms", 0)

        # Obtener tiempos por etapa si están disponibles
        if hasattr(pipeline, "_pipeline_metrics"):
            metrics = pipeline._pipeline_metrics
            results["chunks_processed"] = metrics.chunks_processed
            results["total_processing_time"] = metrics.total_processing_time

        pipeline.shutdown()

    return results


def save_results(results: dict, output_file: Path) -> None:
    """Guardar resultados en JSON."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Cargar resultados previos si existen
    all_results = []
    if output_file.exists():
        with open(output_file) as f:
            all_results = json.load(f)

    all_results.append(results)

    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    logger.info(f"Resultados guardados en: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark SRT2Web Pipeline")
    parser.add_argument("--video", type=str, default=None, help="Ruta al video de prueba")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["sequential", "thread_parallel", "asyncio"],
        default="thread_parallel",
        help="Modo de ejecucion",
    )
    parser.add_argument("--chunks", type=int, default=3, help="Numero de chunks a procesar")
    parser.add_argument("--concurrent", type=int, default=2, help="Max chunks concurrentes")
    parser.add_argument(
        "--output",
        type=str,
        default="tests/benchmark/results.json",
        help="Archivo de salida para resultados",
    )

    args = parser.parse_args()

    # Determinar video de prueba
    if args.video:
        video_path = args.video
    else:
        video_path = str(PROJECT_ROOT / "tests" / "resources" / "short_video.mp4")
        create_dummy_video(Path(video_path))

    # Ejecutar benchmark
    results = run_benchmark(
        video_path=video_path,
        mode=args.mode,
        max_concurrent=args.concurrent,
        num_chunks=args.chunks,
    )

    # Mostrar resultados
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Mode: {results['mode']}")
    print(f"Chunks procesados: {results['chunks_processed']}")
    print(f"Tiempo total: {results['total_time_sec']:.2f}s")
    print(f"Tiempo promedio por chunk: {results['avg_chunk_time_ms']:.2f}ms")
    if results["errors"]:
        print(f"Errores: {len(results['errors'])}")
        for err in results["errors"]:
            print(f"  - {err}")

    # Guardar resultados
    save_results(results, Path(args.output))


if __name__ == "__main__":
    main()
