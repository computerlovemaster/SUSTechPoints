# Dynamic Camera Extrinsic Loading Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make frame switch and playback always apply the current frame's camera extrinsics to box projection, LiDAR projection, and best-camera selection, with static calibration as fallback.

**Architecture:** Keep the backend resolver in `scene_reader.py` as the source of truth for `frame-level > static` priority, keep frame-local calib on each `World`, and ensure all projection consumers read through `world.getCameraCalib()`. The implementation is a reliability pass over the existing path rather than a new subsystem.

**Tech Stack:** Python, CherryPy, vanilla JavaScript, XMLHttpRequest, existing validator script

---

## Chunk 1: Backend Contract And Validation

### Task 1: Confirm and harden camera calib resolution

**Files:**
- Modify: `scene_reader.py`
- Verify: `main.py`
- Verify: `tools/validate_dynamic_camera_calib.py`

- [ ] **Step 1: Inspect the current resolver path**

Read:

```bash
sed -n '241,280p' scene_reader.py
sed -n '166,176p' main.py
```

Expected: `read_camera_calib(scene, frame)` is the only backend entry for frame camera calib and `main.py` only forwards to it.

- [ ] **Step 2: Write down the intended resolver behavior before editing**

Target logic:

```python
if os.path.isfile(frame_calib_file):
    target_file = frame_calib_file
elif os.path.isfile(static_calib_file):
    target_file = static_calib_file
else:
    target_file = None
```

Expected: no backend path returns static calib when a frame-level file exists.

- [ ] **Step 3: Tighten resolver edge handling if needed**

Implementation shape:

```python
try:
    with open(target_file) as f:
        calib[camera_name] = json.load(f)
except (OSError, json.JSONDecodeError):
    continue
```

Expected: one broken camera calib file does not break the whole frame response.

- [ ] **Step 4: Validate local file priority without the API**

Run:

```bash
python tools/validate_dynamic_camera_calib.py --scene example --frame 000950 --strict --server http://127.0.0.1:8081
```

Expected: if the local sample data is valid, local checks pass; if the server is not running yet, API will fail and that is acceptable at this step.

- [ ] **Step 5: Start the backend and validate API consistency**

Run:

```bash
python main.py
```

In another shell:

```bash
python tools/validate_dynamic_camera_calib.py --scene example --frame 000950 --strict
```

Expected: validator exits `0` and reports matching API payload for the frame.

- [ ] **Step 6: Commit**

```bash
git add scene_reader.py tools/validate_dynamic_camera_calib.py
git commit -m "fix: harden dynamic camera calib resolution"
```

## Chunk 2: Frontend World Lifecycle

### Task 2: Make frame-local camera calib a required part of world readiness

**Files:**
- Verify: `public/js/world.js`

- [ ] **Step 1: Inspect preload and readiness gates**

Read:

```bash
sed -n '217,310p' public/js/world.js
sed -n '515,530p' public/js/world.js
```

Expected: `frameCalibLoaded` participates in `preloaded()` and `loadCameraCalib()` is called from `preload()`.

- [ ] **Step 2: Keep `getCameraCalib()` world-local**

Target logic:

```js
if (this.frameCalib && this.frameCalib[cameraName]) return this.frameCalib[cameraName];
if (this.sceneMeta?.calib?.camera?.[cameraName]) return this.sceneMeta.calib.camera[cameraName];
return null;
```

Expected: the current frame always overrides scene-level static calib.

- [ ] **Step 3: Harden failed XHR handling if needed**

Implementation shape:

```js
if (xhr.status !== 200) {
    this.frameCalib = {};
}
this.frameCalibLoaded = true;
```

Expected: a calib fetch failure degrades to empty frame-local calib instead of blocking world activation.

- [ ] **Step 4: Smoke-check world activation**

Run the app, switch frames manually, and confirm:

```text
world.preloaded() only becomes true after camera calib fetch returns
```

Expected: no frame loads with stale image projection from the previous frame.

- [ ] **Step 5: Commit**

```bash
git add public/js/world.js
git commit -m "fix: stabilize world frame camera calib lifecycle"
```

## Chunk 3: Projection Consumers

### Task 3: Ensure all image projections consume current-frame calib

**Files:**
- Modify: `public/js/image.js`
- Verify: `public/js/calib.js`

- [ ] **Step 1: Audit all projection entry points**

Run:

```bash
rg -n "getCameraCalib|sceneMeta.calib.camera|extrinsic" public/js/image.js public/js/calib.js
```

Expected: projection code paths are easy to enumerate before editing.

- [ ] **Step 2: Remove or replace any direct static-calib reads**

Target pattern:

```js
let calib = world.getCameraCalib(cameraName);
if (!calib || !calib.extrinsic) {
    return null;
}
```

Expected: box projection, point projection, and best-camera selection all read from the active world's calib map.

- [ ] **Step 3: Keep missing-calib behavior non-fatal**

Implementation shape:

```js
if (!calib) {
    return;
}
```

Expected: one camera can be skipped while the rest of the UI stays usable.

- [ ] **Step 4: Manual projection smoke test**

Verify three cases:

```text
frame-level calib frame: projection visibly changes with frame
static-only frame: projection still works
missing-calib camera: that camera skips projection without console-breaking errors
```

- [ ] **Step 5: Commit**

```bash
git add public/js/image.js public/js/calib.js
git commit -m "fix: use current-frame camera calib in image projection"
```

## Chunk 4: Frame Switch And Playback Refresh

### Task 4: Verify that switch-frame and playback share the same redraw path

**Files:**
- Verify: `public/js/editor.js`
- Verify: `public/js/play.js`
- Verify: `public/js/data.js`

- [ ] **Step 1: Inspect the active-world handoff**

Read:

```bash
sed -n '2295,2310p' public/js/editor.js
sed -n '57,90p' public/js/play.js
sed -n '411,435p' public/js/data.js
```

Expected: both manual frame switch and playback activate a world and trigger `imageContextManager.attachWorld(world)` plus `render_2d_image()`.

- [ ] **Step 2: Fix any stale-world or missing-rerender path**

Target behavior:

```js
this.imageContextManager.attachWorld(world);
this.imageContextManager.render_2d_image();
```

Expected: the image panel always redraws using the world that was just activated.

- [ ] **Step 3: Playback smoke test**

Run the app and test:

```text
start on frame A
play through frame B and C
observe camera projection updates on each frame without page reload
pause and resume without losing correct projection
```

- [ ] **Step 4: Commit**

```bash
git add public/js/editor.js public/js/play.js public/js/data.js
git commit -m "fix: refresh image projection on frame activation"
```

## Chunk 5: Documentation And Acceptance

### Task 5: Document data layout and verification workflow

**Files:**
- Modify: `doc/install_from_source.md`
- Modify: `README_cn.md`
- Create: `docs/superpowers/specs/2026-03-17-dynamic-camera-extrinsic-loading-design.md`

- [ ] **Step 1: Document the supported directory layout**

Document:

```text
data/<scene>/calib/camera/<camera>.json
data/<scene>/calib/camera/<camera>/<frame>.json
priority: frame-level > static > skip projection
```

- [ ] **Step 2: Document the validator usage**

Document commands:

```bash
python tools/validate_dynamic_camera_calib.py --scene example --frame 000950
python tools/validate_dynamic_camera_calib.py --scene example --strict
```

- [ ] **Step 3: Record the final acceptance checklist**

Checklist:

```text
[ ] manual frame switch updates box projection
[ ] manual frame switch updates LiDAR projection
[ ] playback updates projection per frame
[ ] static fallback works
[ ] missing camera calib degrades safely
```

- [ ] **Step 4: Commit**

```bash
git add doc/install_from_source.md README_cn.md docs/superpowers/specs/2026-03-17-dynamic-camera-extrinsic-loading-design.md
git commit -m "docs: document dynamic camera extrinsic loading"
```

Plan complete and saved to `docs/superpowers/plans/2026-03-17-dynamic-camera-extrinsic-loading.md`. Ready to execute?
