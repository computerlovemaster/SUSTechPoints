#!/usr/bin/env python3
"""Validate dynamic camera calibration priority and API consistency.

Checks for a scene/frame set:
1) Local calib source resolution: dynamic > static > missing
2) Calib format validity (extrinsic/intrinsic shape + numeric)
3) API consistency with /load_camera_calib

Exit codes:
- 0: pass
- 1: validation failure (or warnings in --strict mode)
- 2: runtime error (arg/io/network/json)
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate dynamic camera calib data and /load_camera_calib API behavior"
    )
    parser.add_argument("--scene", required=True, help="Scene name under data root")
    parser.add_argument("--frame", help="Single frame id (without extension)")
    parser.add_argument("--data-root", default="./data", help="Dataset root path")
    parser.add_argument("--server", default="http://127.0.0.1:8081", help="Server base URL")
    parser.add_argument("--api-only", action="store_true", help="Run API checks only")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    return parser.parse_args()


def is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_calib_obj(calib: object, label: str) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(calib, dict):
        errors.append(f"{label}: calib is not an object")
        return errors, warnings

    extrinsic = calib.get("extrinsic")
    intrinsic = calib.get("intrinsic")

    if not isinstance(extrinsic, list):
        errors.append(f"{label}: extrinsic missing or not list")
    else:
        if len(extrinsic) != 16:
            errors.append(f"{label}: extrinsic length expected 16, got {len(extrinsic)}")
        bad_idx = [i for i, v in enumerate(extrinsic) if not is_number(v)]
        if bad_idx:
            errors.append(f"{label}: extrinsic non-numeric values at indexes {bad_idx[:5]}")

    if not isinstance(intrinsic, list):
        errors.append(f"{label}: intrinsic missing or not list")
    else:
        if len(intrinsic) not in (9, 16):
            errors.append(f"{label}: intrinsic length expected 9 or 16, got {len(intrinsic)}")
        bad_idx = [i for i, v in enumerate(intrinsic) if not is_number(v)]
        if bad_idx:
            errors.append(f"{label}: intrinsic non-numeric values at indexes {bad_idx[:5]}")

    rect = calib.get("rect")
    if rect is not None:
        if not isinstance(rect, list):
            warnings.append(f"{label}: rect exists but is not list")
        elif len(rect) not in (9, 16):
            warnings.append(f"{label}: rect length unusual (expected 9 or 16, got {len(rect)})")

    return errors, warnings


def find_camera_names(scene_path: str) -> List[str]:
    names = set()

    camera_root = os.path.join(scene_path, "camera")
    if os.path.isdir(camera_root):
        for entry in os.listdir(camera_root):
            if os.path.isdir(os.path.join(camera_root, entry)):
                names.add(entry)

    calib_root = os.path.join(scene_path, "calib", "camera")
    if os.path.isdir(calib_root):
        for entry in os.listdir(calib_root):
            full = os.path.join(calib_root, entry)
            if os.path.isfile(full) and entry.endswith(".json"):
                names.add(os.path.splitext(entry)[0])
            elif os.path.isdir(full):
                names.add(entry)

    return sorted(names)


def find_frames(scene_path: str, camera_names: List[str], frame_override: Optional[str]) -> List[str]:
    if frame_override:
        return [frame_override]

    frames = set()
    lidar_root = os.path.join(scene_path, "lidar")
    if os.path.isdir(lidar_root):
        for entry in os.listdir(lidar_root):
            full = os.path.join(lidar_root, entry)
            if os.path.isfile(full):
                frames.add(os.path.splitext(entry)[0])

    if not frames:
        camera_root = os.path.join(scene_path, "camera")
        for camera_name in camera_names:
            cam_dir = os.path.join(camera_root, camera_name)
            if not os.path.isdir(cam_dir):
                continue
            for entry in os.listdir(cam_dir):
                full = os.path.join(cam_dir, entry)
                if os.path.isfile(full):
                    frames.add(os.path.splitext(entry)[0])

    return sorted(frames)


def resolve_expected_calib(
    scene_path: str, camera_name: str, frame: str
) -> Tuple[str, Optional[str], Optional[Dict], Optional[str], Optional[Dict]]:
    """Return expected source and related payloads.

    Returns:
      expected_source, expected_path, expected_data, dynamic_path, dynamic_data
    """
    calib_root = os.path.join(scene_path, "calib", "camera")
    dynamic_path = os.path.join(calib_root, camera_name, f"{frame}.json")
    static_path = os.path.join(calib_root, f"{camera_name}.json")

    dynamic_data = None
    static_data = None

    if os.path.isfile(dynamic_path):
        dynamic_data = load_json(dynamic_path)
    if os.path.isfile(static_path):
        static_data = load_json(static_path)

    if dynamic_data is not None:
        return "dynamic", dynamic_path, dynamic_data, dynamic_path, dynamic_data
    if static_data is not None:
        return "static", static_path, static_data, dynamic_path, dynamic_data
    return "missing", None, None, dynamic_path, dynamic_data


def fetch_api_calib(server: str, scene: str, frame: str) -> Tuple[Dict, str]:
    query = urllib.parse.urlencode({"scene": scene, "frame": frame})
    url = f"{server.rstrip('/')}/load_camera_calib?{query}"
    req = urllib.request.Request(url=url, method="GET")

    with urllib.request.urlopen(req, timeout=8) as resp:
        text = resp.read().decode("utf-8")

    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise RuntimeError(f"API response is not object: {url}")

    return payload, url


def print_issue_list(level: str, issues: List[str]) -> None:
    for issue in issues:
        print(f"{level}: {issue}")


def main() -> int:
    args = parse_args()

    try:
        scene_path = os.path.join(args.data_root, args.scene)
        if not os.path.isdir(scene_path):
            print(f"RUN ERROR: scene path does not exist: {scene_path}")
            return 2

        camera_names = find_camera_names(scene_path)
        frames = find_frames(scene_path, camera_names, args.frame)

        if not camera_names:
            print(f"RUN ERROR: no camera names found under {scene_path}")
            return 2
        if not frames:
            print(f"RUN ERROR: no frames found for scene {args.scene}")
            return 2

        validation_pass = 0
        validation_fail = 0
        warnings_count = 0

        print("DETAIL")

        for frame in frames:
            expected_by_camera: Dict[str, Tuple[str, Optional[Dict], Optional[Dict], Optional[Dict]]] = {}

            if not args.api_only:
                for camera_name in camera_names:
                    expected_source, expected_path, expected_data, dynamic_path, dynamic_data = resolve_expected_calib(
                        scene_path, camera_name, frame
                    )

                    static_path = os.path.join(scene_path, "calib", "camera", f"{camera_name}.json")
                    static_data = load_json(static_path) if os.path.isfile(static_path) else None

                    expected_by_camera[camera_name] = (
                        expected_source,
                        expected_data,
                        dynamic_data,
                        static_data,
                    )

                    print(
                        f"DETAIL: frame={frame} camera={camera_name} expected_source={expected_source} "
                        f"path={expected_path if expected_path else '-'}"
                    )

                    if expected_source in ("dynamic", "static") and expected_data is not None:
                        errs, warns = validate_calib_obj(
                            expected_data,
                            f"local frame={frame} camera={camera_name} source={expected_source}",
                        )
                        if errs:
                            validation_fail += len(errs)
                            print_issue_list("FAIL", errs)
                        else:
                            validation_pass += 1

                        if warns:
                            warnings_count += len(warns)
                            print_issue_list("WARN", warns)

            try:
                api_payload, url = fetch_api_calib(args.server, args.scene, frame)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
                print(f"API CHECK: frame={frame} status=ERROR url={args.server.rstrip('/')}/load_camera_calib")
                print(f"RUN ERROR: {exc}")
                return 2

            print(f"API CHECK: frame={frame} url={url} cameras_returned={len(api_payload)}")

            for camera_name, calib in api_payload.items():
                errs, warns = validate_calib_obj(calib, f"api frame={frame} camera={camera_name}")
                if errs:
                    validation_fail += len(errs)
                    print_issue_list("FAIL", errs)
                else:
                    validation_pass += 1
                if warns:
                    warnings_count += len(warns)
                    print_issue_list("WARN", warns)

            if args.api_only:
                continue

            # Compare API result against expected priority/source per camera
            for camera_name in camera_names:
                expected_source, expected_data, dynamic_data, static_data = expected_by_camera[camera_name]
                api_calib = api_payload.get(camera_name)

                actual_source = "missing"
                if api_calib is not None:
                    if dynamic_data is not None and api_calib == dynamic_data:
                        actual_source = "dynamic"
                    elif static_data is not None and api_calib == static_data:
                        actual_source = "static"
                    else:
                        actual_source = "unknown"

                if expected_source != actual_source:
                    validation_fail += 1
                    print(
                        f"FAIL: frame={frame} camera={camera_name} "
                        f"source_mismatch expected={expected_source} actual={actual_source}"
                    )
                else:
                    validation_pass += 1

                if expected_source in ("dynamic", "static"):
                    if api_calib is None:
                        validation_fail += 1
                        print(f"FAIL: frame={frame} camera={camera_name} missing in API response")
                    elif expected_data is not None and api_calib != expected_data:
                        validation_fail += 1
                        print(
                            f"FAIL: frame={frame} camera={camera_name} payload_diff "
                            "expected source file content but API differs"
                        )

            extra_cameras = sorted(set(api_payload.keys()) - set(camera_names))
            if extra_cameras:
                warnings_count += len(extra_cameras)
                print(
                    f"WARN: frame={frame} API returned unexpected cameras not in scene scan: {extra_cameras}"
                )

        print("SUMMARY")
        print(f"SUMMARY: scene={args.scene}")
        print(f"SUMMARY: mode={'api-only' if args.api_only else 'data+api'}")
        print(f"SUMMARY: frames={len(frames)} cameras={len(camera_names)}")
        print(f"SUMMARY: pass={validation_pass} fail={validation_fail} warn={warnings_count}")

        if validation_fail > 0:
            return 1
        if args.strict and warnings_count > 0:
            return 1
        return 0

    except (OSError, json.JSONDecodeError) as exc:
        print(f"RUN ERROR: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
