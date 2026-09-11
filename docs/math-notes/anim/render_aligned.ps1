# Sequential re-render of the three cascade modes from the corrected
# (aligned) barycenter layout. One Blender at a time; per-version logs;
# new version tags so nothing is overwritten.
$B = "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
$S = "F:\video-game-projects\skyrim-alchmey-effect-finder\docs\math-notes\anim\build_scene.py"
$JSON = "F:\video-game-projects\skyrim-alchmey-effect-finder\docs\math-notes\anim\plans-uesp.json"
$R = "F:\video-game-projects\skyrim-alchmey-effect-finder\docs\math-notes\anim\render"
$jobs = @(
  @{ mode = "brew";       tag = "v13-eq-brew-aligned" },
  @{ mode = "ingredient"; tag = "v14-eq-ingredients-aligned" },
  @{ mode = "effect";     tag = "v15-eq-effects-aligned" }
)
# PowerShell variable names are case-insensitive: a loop variable named $j
# silently clobbered the JSON path in $J (two failed launches, 2026-09-10).
foreach ($job in $jobs) {
  $log = Join-Path $R ("render-" + [string]$job.tag + ".log")
  "=== $(Get-Date -Format s) start $([string]$job.tag)" | Out-File $log -Encoding utf8
  $mode = [string]$job.mode
  $tag  = [string]$job.tag
  "args: $mode $JSON $tag" | Out-File $log -Append -Encoding utf8
  & $B -b --python $S -a -- $mode $JSON $tag 2>&1 | Out-File $log -Append -Encoding utf8
  "=== $(Get-Date -Format s) exit $LASTEXITCODE $([string]$job.tag)" | Out-File $log -Append -Encoding utf8
}
"=== ALL DONE $(Get-Date -Format s)" | Out-File (Join-Path $R "render-aligned.done") -Encoding utf8
