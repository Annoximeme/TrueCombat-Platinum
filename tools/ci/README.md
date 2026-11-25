# Cloud builds

Builds and tests that used to run on the development PC now run on GitHub's
build machines (free for this public repository). The PC is only needed for
in-game DX12/OpenGL tests (real GPU) and for packaging a release. Nothing here
runs on the VPS, so the live game servers are never slowed down.

| Job | What it does | Typical time |
| --- | --- | --- |
| `windows` | Full Windows x64 cross-build with the same LLVM-MinGW release and flags as the PC: `etl.exe`, `etlded.exe`, DX12 (with DLSS) and OpenGL renderers, OpenAL, UI, `qagame`/`cgame`, launcher, installer, master server; runs the native probes under Wine | ~10 min |
| `linux` | Linux dedicated server (public kit build) | ~5 min |
| `eac` | Linux dedicated server with Easy Anti-Cheat, as used on the official servers | ~5 min |
| `bots` | Headless soak: the Linux build runs each map with a full server of bots; fails on a crash, a fatal error, a hang or bots that never join. Records the server's CPU per map (average and worst 15 s window) | 2-20 min per map |
| `scan` | Provenance / tool metadata scan of the whole source tree: C2PA and JUMBF manifests, metadata naming an AI tool, inside pk3 members and inside images compiled into the launcher as byte arrays. The `windows` job scans the built game the same way | ~1 min |

## Privacy

The repository is public, and so are workflow logs and artifacts. So:

- Unreleased source and SDK headers live in **hidden draft releases** (visible only
  to people with write access): `ci-deps` holds the EOS SDK headers, `ci-<name>`
  holds one build request and its results.
- For a request, compiler output is never printed in the public log (`QUIET=1`);
  logs, binaries and summaries go into the request's draft.
- A published release's own source can be built openly (pull requests to this
  folder do that as a self-test).

## From the PC (or any machine with `gh` logged in)

```powershell
# send a candidate tree: only files that differ from the base release (usually a few MB)
python tools\ci\request.py send --root C:\TrueCombatWork\integ038\src --base v0.37.3-sandbox33 --name integ038
python tools\ci\request.py status --name integ038 --wait 30     # pass/fail per job
python tools\ci\request.py fetch  --name integ038 --out C:\TrueCombatWork\integ038\cloud
python tools\ci\request.py clean  --name integ038                # delete the draft when done
```

Options: `--jobs windows,linux,eac,bots`, `--maps "obj_village obj_snow"`,
`--minutes 4` (per map, max 20), `--dry-run` (list what would be sent).
The first `send` also puts the EOS SDK headers into `ci-deps` if they are missing.

## From a cloud thread

Cloud sessions cannot create releases, so they build in their own container
with the same script (no PC, no VPS):

```sh
tools/ci/setup-toolchain.sh ~/toolchain                                  # once, ~1 min
unzip -q /mnt/project-files/ci/eos-sdk-include.zip -d ~/eos              # optional, enables EAC code
LLVM_MINGW=~/toolchain/llvm-mingw SL_SDK=~/toolchain/streamline EOS_INCLUDE=~/eos/Include \
  tools/ci/build-windows.sh <source tree> out                            # Windows build + probes (needs wine)
tools/linux-server/build-linux-server.sh <source tree> linux             # Linux server
tools/ci/bots-soak.sh linux v0.37.3-sandbox33 "obj_village obj_snow" 3  # bots soak
```

A source tree is a release's `f__source__native-sandbox-source.zip` unpacked, with
a kit's patches applied on top. `tools/ci/compose-source.sh <base tag> <out>` fetches
and unpacks the base.

## Kit gate (before a kit goes to the release integrator)

Every feature kit passes this before the integrator takes it, so broken patches, metadata and
build failures surface in the feature's own thread instead of mid-release on the PC:

```sh
tools/ci/kit-gate.sh v0.38.0-sandbox34 <kit folder> "obj_village obj_snow" 3
```

Before a release is published its tag does not exist yet, so the base can also be the frozen candidate's
source as a zip or folder (`tools/ci/kit-gate.sh /mnt/project-files/release-speed/base/<zip> <kit>`); the
bots soak then uses the newest published release's game data under the kit's own server and modules.

The kit folder holds `patches/*.patch` (applied in name order with `git apply`, no fuzz) and optionally
`files/` (copied over the tree). The script composes the base release source, applies the kit, scans
it, cross-builds Windows (with the probes when wine is installed), builds the Linux server and runs the
bots soak. It writes `kit-gate/SUMMARY.md` with the base tag and the kit's checksum; put that summary
next to the kit manifest. The integrator accepts only kits whose summary passed on the current base and
matches the kit's checksum.

The base can also be a checkout of the development repository: `build-windows.sh` then copies the
shipped renderer files from `experiments/dlss/source` into the engine first, as the PC candidate build
does. Set `BUILD_CACHE=<folder>` to share a compiler cache (ccache) between gate runs; a second gate in
another work folder reuses almost every object.

## What still needs the PC

- In-game tests with a real GPU (DX12 and OpenGL screenshots, feel, audio devices).
- Packaging and publishing a release (`package_from_candidate.py`, `fast_publish.py`),
  only with Gianni's go.

## Files

| File | Purpose |
| --- | --- |
| `build-windows.sh` | Windows cross-build + probes from a source tree |
| `setup-toolchain.sh` | Downloads pinned LLVM-MinGW 20261020 and Streamline 2.14.16 headers |
| `compose-source.sh` | Base release source + a request's changed files |
| `bots-soak.sh` | Bots-only soak of a Linux server build, with server CPU per map |
| `kit-gate.sh` | Kit gate for feature threads: apply, scan, build, soak, summary |
| `scan_metadata.py` | Provenance / tool metadata scanner (files, folders, pk3 members, embedded image arrays) |
| `request.py` | Send a tree, check status, fetch results, clean up |
| `draft.py` | Hidden draft release storage (used by the above and the workflow) |
| `result.py` | Per-job result file for a request |
| `platinum.ico` | Engine icon, which source snapshots up to 0.37.3 leave out |
