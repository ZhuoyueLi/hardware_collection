"""ZED camera publisher that streams frames over ZeroLanCom."""

from __future__ import annotations

import argparse
import logging
import signal
import time
from pathlib import Path
import threading
from typing import Any, Dict, List

import yaml

from hardware_collection.camera.camera_zed_sdk import ZED as ZEDCamera
import pyzlc

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream ZED frames over ZeroLanCom")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/zed_publisher.yaml",
        help="Path to YAML config file",
    )
    return parser.parse_args()


def load_config(path: str) -> Dict[str, Any]:
    cfg_path = Path(path)
    if not cfg_path.is_file():
        logger.warning("Config file not found at %s, using CLI/defaults", cfg_path)
        return {}

    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config at {cfg_path} must be a mapping/dict")

    return data


def _merge_camera_config(
    root_cfg: Dict[str, Any],
    camera_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    defaults = {
        "width": 1280,
        "height": 720,
        "fps": 30,
        "depth_mode": "PERFORMANCE",
        "show_preview": False,
        "log_interval": 60,
    }
    merged = {**defaults, **root_cfg, **camera_cfg}
    return merged


def _resolve_camera_configs(root_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "camera_configs" not in root_cfg:
        # Legacy single-camera config.
        return [_merge_camera_config({}, root_cfg)]

    config_dir = Path(root_cfg.get("zed_config_dir", ""))
    camera_files = root_cfg.get("camera_configs") or []
    if not camera_files:
        raise ValueError("camera_configs must be a non-empty list in zed_publisher.yaml")

    camera_cfgs: List[Dict[str, Any]] = []
    for filename in camera_files:
        cfg_path = config_dir / filename
        camera_cfg = load_config(str(cfg_path))
        camera_cfgs.append(_merge_camera_config(root_cfg, camera_cfg))
    return camera_cfgs


def _validate_camera_config(cfg: Dict[str, Any]) -> None:
    required_fields = [
        "device_id",
        "publish_topic",
        "width",
        "height",
        "fps",
        "depth_mode",
        "show_preview",
        "log_interval",
        "zlc_config",
    ]
    for field in required_fields:
        if field not in cfg or cfg[field] in (None, ""):
            raise ValueError(f"Missing required field '{field}' in the YAML configuration")


def _camera_loop(
    camera: ZEDCamera,
    log_interval: int,
    stop_event: threading.Event,
) -> None:
    frames_sent = 0
    last_report_time = time.time()
    try:
        while not stop_event.is_set():
            camera.publish_frame()
            frames_sent += 1

            now = time.time()
            if now - last_report_time >= log_interval:
                elapsed = now - last_report_time
                fps = frames_sent / elapsed if elapsed > 0 else 0.0
                logger.info(
                    "[%s] Published %d frames (%.2f FPS)",
                    camera.device_name,
                    frames_sent,
                    fps,
                )
                frames_sent = 0
                last_report_time = now
    except Exception as exc:  # pragma: no cover - runtime feedback only
        logger.error("[%s] Camera loop stopped: %s", camera.device_name, exc)
        stop_event.set()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    root_cfg = load_config(args.config)
    camera_cfgs = _resolve_camera_configs(root_cfg)

    cameras: List[ZEDCamera] = []
    threads: List[threading.Thread] = []
    stop_event = threading.Event()

    for cfg in camera_cfgs:
        _validate_camera_config(cfg)
        cameras.append(
            ZEDCamera(
                device_id=str(cfg["device_id"]),
                height=int(cfg["height"]),
                width=int(cfg["width"]),
                fps=int(cfg["fps"]),
                depth_mode=str(cfg["depth_mode"]),
                show_preview=bool(cfg["show_preview"]),
                publish_topic=cfg["publish_topic"],
                zlc_config=str(cfg["zlc_config"]),
            )
        )

    def _shutdown_handler(signum, _frame):
        logger.info("Received signal %s, shutting down...", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    try:
        pyzlc.info("[ZEDCamNode] Camera publisher started")
        for camera, cfg in zip(cameras, camera_cfgs):
            thread = threading.Thread(
                target=_camera_loop,
                args=(camera, int(cfg["log_interval"]), stop_event),
                daemon=True,
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
    except Exception as exc:  # pragma: no cover - runtime feedback only
        logger.error("Publisher stopped due to error: %s", exc)
        return 1
    finally:
        stop_event.set()
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        for camera in cameras:
            camera.close()
        logger.info("All cameras closed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
