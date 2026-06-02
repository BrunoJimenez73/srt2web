"""
Profile pipeline — benchmark with per-stage timing breakdown.

Captures per-module latency, identifies bottlenecks, and saves structured
results for trend comparison across optimizations.

Usage:
    python scripts/profile_pipeline.py
    python scripts/profile_pipeline.py --mode sequential
    python scripts/profile_pipeline.py --chunks 5 --output profiling_results.json
    python scripts/profile_pipeline.py --compare  # run all modes and compare
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import ConfigManager
from core.unified_pipeline import PipelineMode, UnifiedPipeline
from modules.inputs.file_input import FileInput
from modules.outputs.hls_output import HLSOutput

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("profile")


def create_dummy_video(output_path: Path, duration: int = 15) -> None:
    if output_path.exists():
        logger.info(f"Video exists: {output_path}")
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
    logger.info(f"Creating dummy video: {output_path}")
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=60)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        raise
    except FileNotFoundError:
        logger.error("FFmpeg not found")
        raise


def run_profile(
    video_path: str,
    mode: str = "thread_parallel",
    max_concurrent: int = 2,
    num_chunks: int = 5,
) -> dict:
    logger.info(f"Profile: mode={mode}, chunks={num_chunks}, concurrent={max_concurrent}")

    config_manager = ConfigManager()
    config = config_manager.load_config()
    config.modules.transcriber.model = "tiny"
    config.pipeline.chunk_duration_sec = 5
    config.output.web.segment_duration = 5

    pipeline_mode = PipelineMode(mode)
    pipeline = UnifiedPipeline(
        mode=pipeline_mode,
        max_concurrent_chunks=max_concurrent,
        buffer_size=5,
    )

    file_input = FileInput()
    file_input.configure({"file_path": video_path, "chunk_duration_sec": 5})
    pipeline.set_input_source(file_input)

    hls_output = HLSOutput()
    hls_output.configure(
        {
            "output_dir": str(PROJECT_ROOT / "temp_profile_hls"),
            "segment_duration": 5,
            "list_size": 3,
        }
    )
    pipeline.set_output_sink(hls_output)

    pipeline.register_module(file_input)

    chunks_processed = [0]
    has_sync = hasattr(pipeline, "_process_chunk_sync")
    if has_sync:
        original = pipeline._process_chunk_sync

        def limit_chunks(*a, **kw):
            if chunks_processed[0] >= num_chunks:
                asyncio.run(pipeline.stop())
                return None
            chunks_processed[0] += 1
            return original(*a, **kw)

        pipeline._process_chunk_sync = limit_chunks

    start_time = time.perf_counter()
    errors: list[str] = []
    try:
        pipeline.start()
        while pipeline.get_status()["state"] == "running":
            time.sleep(0.5)
            if chunks_processed[0] >= num_chunks:
                break
        asyncio.run(pipeline.stop())
    except Exception as e:
        errors.append(str(e))
        logger.error(f"Profile error: {e}")
    finally:
        wall_time = time.perf_counter() - start_time
        status = pipeline.get_status()
        result = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "max_concurrent": max_concurrent,
            "chunks_requested": num_chunks,
            "chunks_processed": status.get("chunks_processed", chunks_processed[0]),
            "chunks_failed": status.get("chunks_failed", 0),
            "wall_time_sec": round(wall_time, 3),
            "avg_processing_time_ms": status.get("avg_processing_time_ms", 0),
            "module_avg_time_ms": status.get("module_avg_time_ms", {}),
            "module_total_times": status.get("module_total_times", {}),
            "throughput_chunks_per_sec": round(chunks_processed[0] / wall_time, 3) if wall_time > 0 else 0,
            "errors": errors,
        }
        pipeline.shutdown()
    return result


def print_report(result: dict) -> None:
    print()
    print("=" * 64)
    print("  PERFORMANCE PROFILE REPORT")
    print("=" * 64)
    print(f"  Mode:                {result['mode']}")
    print(f"  Chunks:              {result['chunks_processed']}/{result['chunks_requested']}")
    print(f"  Wall time:           {result['wall_time_sec']:.2f}s")
    print(f"  Avg chunk time:      {result['avg_processing_time_ms']:.1f}ms")
    print(f"  Throughput:          {result['throughput_chunks_per_sec']:.2f} chunks/s")
    if result["chunks_failed"]:
        print(f"  Chunks failed:       {result['chunks_failed']}")
    print("-" * 64)
    print("  Per-Module Timing (avg ms):")
    module_times = result.get("module_avg_time_ms", {})
    if module_times:
        max_name = max(len(n) for n in module_times)
        sorted_mods = sorted(module_times.items(), key=lambda x: -x[1])
        for name, avg in sorted_mods:
            bar_len = int((avg / max(v for _, v in sorted_mods)) * 30) if sorted_mods else 0
            bar = "█" * bar_len
            label = f"{name:>{max_name}}"
            if avg >= 1000:
                print(f"    {label}  {bar}  {avg / 1000:.2f}s")
            else:
                print(f"    {label}  {bar}  {avg:.0f}ms")
    else:
        print("    (no per-module data collected)")
    print("-" * 64)

    # Bottleneck analysis
    if module_times:
        sorted_mods = sorted(module_times.items(), key=lambda x: -x[1])
        bottleneck = sorted_mods[0]
        total = sum(module_times.values())
        pct = (bottleneck[1] / total * 100) if total > 0 else 0
        print(f"  Bottleneck:          {bottleneck[0]} ({bottleneck[1]:.0f}ms, {pct:.0f}% of total)")

        if pct > 50:
            print(f"  ⚠  {bottleneck[0]} dominates processing (>50%). Consider:")
            print(f"      - GPU acceleration for {bottleneck[0]}")
            print("      - Reducing model size or precision")
            print("      - Increasing concurrent chunks")

        if result["mode"] == "sequential" and result["throughput_chunks_per_sec"] < 0.5:
            print("  💡  Low throughput in sequential mode. Try --mode thread_parallel")
    else:
        print("  Bottleneck:          (insufficient data)")
    print("=" * 64)
    print()


def save_results(results: list, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if output_file.exists():
        with open(output_file) as f:
            existing = json.load(f)
    existing.append(results if isinstance(results, dict) else {"runs": results})
    with open(output_file, "w") as f:
        json.dump(existing, f, indent=2)
    logger.info(f"Results saved to {output_file}")


def compare_modes(video_path: str, chunks: int) -> None:
    modes = ["sequential", "thread_parallel", "asyncio"]
    results = []
    for mode in modes:
        print(f"\n  >>> Running mode: {mode}")
        r = run_profile(video_path=video_path, mode=mode, num_chunks=chunks)
        results.append(r)
        print_report(r)

    print("=" * 64)
    print("  MODE COMPARISON")
    print("=" * 64)
    print(f"  {'Mode':<20} {'Chunks':>8} {'Wall Time':>12} {'Avg (ms)':>10} {'Throughput':>12}")
    print("  " + "-" * 62)
    for r in results:
        print(
            f"  {r['mode']:<20} {r['chunks_processed']:>8} {r['wall_time_sec']:>8.2f}s  {r['avg_processing_time_ms']:>8.1f}  {r['throughput_chunks_per_sec']:>8.2f}/s"
        )
    print()
    best = max(results, key=lambda r: r["throughput_chunks_per_sec"])
    print(f"  Best mode: {best['mode']} ({best['throughput_chunks_per_sec']:.2f} chunks/s)")
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(description="SRT2Web Pipeline Profiler")
    parser.add_argument("--video", type=str, default=None, help="Path to test video")
    parser.add_argument(
        "--mode",
        type=str,
        default="thread_parallel",
        choices=["sequential", "thread_parallel", "asyncio"],
        help="Pipeline execution mode",
    )
    parser.add_argument("--chunks", type=int, default=5, help="Number of chunks to process")
    parser.add_argument("--concurrent", type=int, default=2, help="Max concurrent chunks")
    parser.add_argument("--output", type=str, default="scripts/profile_results.json", help="Results output file")
    parser.add_argument("--compare", action="store_true", help="Run all modes and compare")
    args = parser.parse_args()

    if args.video:
        video_path = args.video
    else:
        video_path = str(PROJECT_ROOT / "tests" / "resources" / "short_video.mp4")
        create_dummy_video(Path(video_path))

    if args.compare:
        compare_modes(video_path, args.chunks)
    else:
        result = run_profile(
            video_path=video_path,
            mode=args.mode,
            max_concurrent=args.concurrent,
            num_chunks=args.chunks,
        )
        print_report(result)
        if args.output:
            save_results(result, Path(args.output))


if __name__ == "__main__":
    main()
