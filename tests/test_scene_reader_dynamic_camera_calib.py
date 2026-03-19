import json
import os
import shutil
import tempfile
import unittest

import scene_reader


class ReadCameraCalibTests(unittest.TestCase):
    def setUp(self):
        self._old_root_dir = scene_reader.root_dir
        self.temp_dir = tempfile.mkdtemp(prefix="scene-reader-calib-")
        scene_reader.root_dir = self.temp_dir

    def tearDown(self):
        scene_reader.root_dir = self._old_root_dir
        shutil.rmtree(self.temp_dir)

    def _mkdir(self, *parts):
        path = os.path.join(self.temp_dir, *parts)
        os.makedirs(path, exist_ok=True)
        return path

    def _write_json(self, relpath, payload):
        path = os.path.join(self.temp_dir, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def _write_text(self, relpath, content):
        path = os.path.join(self.temp_dir, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_prefers_frame_level_camera_calib_over_static(self):
        self._mkdir("scene-a", "camera", "front")
        self._mkdir("scene-a", "calib", "camera", "front")
        self._write_json(
            "scene-a/calib/camera/front.json",
            {"extrinsic": [1] * 16, "intrinsic": [2] * 9},
        )
        self._write_json(
            "scene-a/calib/camera/front/000001.json",
            {"extrinsic": [3] * 16, "intrinsic": [4] * 9},
        )

        calib = scene_reader.read_camera_calib("scene-a", "000001")

        self.assertEqual(["front"], sorted(calib.keys()))
        self.assertEqual([3] * 16, calib["front"]["extrinsic"])
        self.assertEqual([4] * 9, calib["front"]["intrinsic"])

    def test_skips_invalid_camera_calib_without_breaking_other_cameras(self):
        self._mkdir("scene-b", "camera", "front")
        self._mkdir("scene-b", "camera", "left")
        self._mkdir("scene-b", "calib", "camera", "left")
        self._write_json(
            "scene-b/calib/camera/front.json",
            {"extrinsic": [5] * 16, "intrinsic": [6] * 9},
        )
        self._write_text(
            "scene-b/calib/camera/left/000002.json",
            "{ this is not valid json }",
        )

        calib = scene_reader.read_camera_calib("scene-b", "000002")

        self.assertEqual(["front"], sorted(calib.keys()))
        self.assertEqual([5] * 16, calib["front"]["extrinsic"])

    def test_includes_cameras_defined_only_by_dynamic_calib_directories(self):
        self._mkdir("scene-c", "camera", "left")
        self._mkdir("scene-c", "calib", "camera", "left")
        self._mkdir("scene-c", "calib", "camera", "right")
        self._write_json(
            "scene-c/calib/camera/left/000003.json",
            {"extrinsic": [7] * 16, "intrinsic": [8] * 9},
        )
        self._write_json(
            "scene-c/calib/camera/right/000003.json",
            {"extrinsic": [9] * 16, "intrinsic": [10] * 9},
        )

        calib = scene_reader.read_camera_calib("scene-c", "000003")

        self.assertEqual(["left", "right"], sorted(calib.keys()))
        self.assertEqual([9] * 16, calib["right"]["extrinsic"])


if __name__ == "__main__":
    unittest.main()
