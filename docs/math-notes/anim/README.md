# The discovery cascade - greedy vs optimal, animated

Companion animation for the alchemy cliff article: two radial
ingredient/effect webs light up brew by brew, side by side. The amber
side follows the greedy planner (76 brews); the ice-blue side follows
the MIP-optimal plan (70 brews), finishes six brews early, takes one
slow breath, and holds still while greedy keeps striking.

Every ignition is exact: the timeline is driven by the app's own
planner and the stored optimal plan, brew for brew, slot for slot -
448 discoverable effect-slots per side, each one an edge.

## Pipeline

```
# 1. data -> timeline JSON (repo root; needs the repo's Python env)
python docs/math-notes/anim/export_plans.py

# 2. JSON -> animated scene, opened interactively...
blender --python docs/math-notes/anim/build_scene.py

# ...or 3. rendered straight to H.264 MP4 (docs/math-notes/anim/render/)
blender -b --python docs/math-notes/anim/build_scene.py -a
```

Built and tested on Blender 5.0. All look parameters (colors, timing,
camera, bloom) are constants at the top of `build_scene.py`; layout
(radial rings, barycenter untangling) lives in `export_plans.py`.
Everything animates through per-object `"lit"` custom properties read
by shared emission materials - no per-object materials, no drivers.

## Files

- `export_plans.py` - rebuilds the UESP-112 world, recomputes the
  greedy plan with `alchemy_helper`'s planner, replays the stored
  optimal plan (`../data/alchemy-mip-results-uesp.json`), verifies both
  light all 448 slots, emits `plans-uesp.json`.
- `build_scene.py` - builds the whole scene from that JSON: nodes,
  edges, keyframes, counters, finish beats, camera, bloom, output.
- `plans-uesp.json` - the committed timeline (regenerable).
- `render/` - render output, untracked.
