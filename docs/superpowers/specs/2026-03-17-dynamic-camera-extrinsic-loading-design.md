# Dynamic Camera Extrinsic Loading Design

## Goal

Make camera projection behave deterministically with frame-level camera extrinsics while preserving the existing static calibration fallback:

- Prefer `data/<scene>/calib/camera/<camera>/<frame>.json`
- Fallback to `data/<scene>/calib/camera/<camera>.json`
- If neither exists, skip projection for that camera without breaking world loading

This scope only covers loading and applying dynamic camera extrinsics during frame switch and playback. It does not include editing or saving frame-level camera calibration from the UI.

## Current State

The codebase already contains most of the required path:

- Backend API [`main.py`](/home/flint/code/SUSTech/main.py#L171) exposes `/load_camera_calib`
- Backend resolver [`scene_reader.py`](/home/flint/code/SUSTech/scene_reader.py#L241) already loads frame-level calib before static calib
- World preload [`public/js/world.js`](/home/flint/code/SUSTech/public/js/world.js#L255) fetches frame calib before a world is considered ready
- Projection paths in [`public/js/image.js`](/home/flint/code/SUSTech/public/js/image.js#L1078) use `world.getCameraCalib()`
- Frame switch and playback both activate a new world and trigger image redraw in [`public/js/editor.js`](/home/flint/code/SUSTech/public/js/editor.js#L2295) and [`public/js/play.js`](/home/flint/code/SUSTech/public/js/play.js#L57)

That means the remaining work is not a greenfield feature. It is a reliability pass: confirm the end-to-end contract, fix any missing edge handling, and add repeatable verification.

## Target Behavior

For every active frame:

1. The backend returns one calibration object per camera, resolved with `frame-level > static`.
2. The frontend world stores the returned set as frame-local calibration state.
3. Every camera-dependent projection uses the current world's calibration set, never stale calibration from another frame.
4. Switching frames or playing frames automatically updates:
   - 3D box projection on camera images
   - LiDAR point projection on camera images
   - automatic best-camera selection
5. Missing calibration for one camera only disables that camera's projection. It must not block world activation.

## Architecture

### 1. Backend Resolution Contract

The backend remains the single source of truth for frame calibration resolution.

Resolver contract:

```python
def read_camera_calib(scene, frame):
    for camera_name in discover_camera_names(scene):
        if exists(frame_level_path(scene, camera_name, frame)):
            use(frame_level_path(scene, camera_name, frame))
        elif exists(static_path(scene, camera_name)):
            use(static_path(scene, camera_name))
        else:
            skip(camera_name)
```

Important constraints:

- Camera discovery must include both camera directories and static calib JSON names.
- Returned payload must be an object keyed by camera name.
- The resolver must tolerate partial scene data.

### 2. Frontend World Calibration Lifecycle

Each `World` owns a frame-local calibration map:

```js
this.frameCalib = {};
this.frameCalibLoaded = false;
```

Lifecycle rules:

- `loadCameraCalib()` runs during world preload.
- `preloaded()` must stay false until frame calib fetch completes.
- `getCameraCalib(cameraName)` must always read from:
  1. `world.frameCalib[cameraName]`
  2. fallback `sceneMeta.calib.camera[cameraName]`
  3. `null`

This keeps calibration state isolated to the world instance that matches the current frame.

### 3. Projection Consumers

All projection consumers must read calibration through `world.getCameraCalib()`:

- best-camera selection
- box-to-image projection
- LiDAR-to-image projection
- calibration debug view

No projection code should directly read `sceneMeta.calib.camera[...]` once a `World` is active, because that would bypass frame-local overrides.

### 4. Frame Switch and Playback

Frame switch and playback must share the same behavior:

- load or reuse a `World` for the requested frame
- wait until preload completes, including frame calib
- activate the world
- reattach image contexts to the newly active world
- redraw 2D image projections

This is already mostly present. The work here is to confirm there is no stale state path left behind.

## Error Handling

Expected degradation behavior:

- Missing frame-level file: fallback to static calib
- Missing static file too: skip that camera for projection
- Invalid JSON or invalid calib structure: log the issue, treat that camera as unavailable for projection, continue loading the world
- API failure for `/load_camera_calib`: world should still load with empty frame calib and only use static scene meta where available

No error in one camera should block annotation on the frame.

## Verification Strategy

Verification must cover both resolution and rendering.

### Data/API verification

Use [`tools/validate_dynamic_camera_calib.py`](/home/flint/code/SUSTech/tools/validate_dynamic_camera_calib.py) to confirm:

- local file priority
- calib shape validity
- API response consistency

### Frontend smoke verification

Manual acceptance must cover:

1. A frame with frame-level calib that differs from static calib
2. A frame without frame-level calib that falls back to static calib
3. A camera missing both frame-level and static calib
4. Sequential playback across frames with different calib sources

## Files Expected To Matter

- [`scene_reader.py`](/home/flint/code/SUSTech/scene_reader.py)
- [`main.py`](/home/flint/code/SUSTech/main.py)
- [`public/js/world.js`](/home/flint/code/SUSTech/public/js/world.js)
- [`public/js/image.js`](/home/flint/code/SUSTech/public/js/image.js)
- [`public/js/editor.js`](/home/flint/code/SUSTech/public/js/editor.js)
- [`public/js/play.js`](/home/flint/code/SUSTech/public/js/play.js)
- [`tools/validate_dynamic_camera_calib.py`](/home/flint/code/SUSTech/tools/validate_dynamic_camera_calib.py)
- [`doc/install_from_source.md`](/home/flint/code/SUSTech/doc/install_from_source.md)
- [`README_cn.md`](/home/flint/code/SUSTech/README_cn.md)

## Non-Goals

- UI-based editing or saving of frame-level camera calibration
- deriving camera extrinsics from ego pose at runtime
- refactoring all calibration systems into a new abstraction layer

## Recommended Delivery Strategy

Use a minimal-change pass:

1. verify the existing path end to end
2. fix only the places where stale or missing behavior remains
3. add repeatable validation so the feature stays correct
