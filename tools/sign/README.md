# Code signing (SignPath Foundation)

New releases trip desktop antivirus reputation checks because every engine build is a new,
unsigned file. The fix is to sign every program we build with the free open source certificate
from SignPath Foundation. SignPath signs only what GitHub Actions built from this public
repository, so the release binaries are built here, not on the development PC.

| File | Purpose |
| --- | --- |
| `.github/workflows/release-sign.yml` | Builds the Windows release binaries of a release on GitHub-hosted runners, stages them as shipped, uploads `unsigned-<tag>`, sends them to SignPath, waits for the maintainer's approval and uploads `signed-<tag>` |
| `stage_release_binaries.py` | Build output -> shipped names and layout, debug data and symbols removed, valid PE checksum, `MANIFEST.json` |
| `check_signed.py` | Release gate check: each of our binaries is signed by SignPath Foundation, the signature is valid, the version resource names the product with one version for all files, and (with `--unsigned-ref`) the signed file is the gated unsigned file plus a signature and nothing else |
| `signpath-artifact-configuration.xml` | What SignPath signs inside the artifact, with product name and version restrictions |

## Flow per release

1. Freeze: the release source is published (source repository or release source zip).
2. Run **Release binaries (build and sign)** with the release tag. The `build` job produces
   `unsigned-<tag>`; the full regression on the PC runs on exactly these binaries.
3. When the gate passes, approve the signing request in SignPath. The `sign` job downloads the
   signed files and runs `check_signed.py --unsigned-ref`, which proves the signature is the only
   change, so no second regression is needed.
4. Packaging uses `signed-<tag>` and refuses unsigned binaries (`package_from_candidate.py` sign gate).
   The Easy Anti-Cheat integrity catalogue and the update feed hashes are made from the signed files.

Vendor files are never signed by us: Easy Anti-Cheat and EOS SDK (Epic), DLSS (NVIDIA), the
Visual C++ runtime (Microsoft). OpenAL Soft is an unmodified upstream library and is allowed unsigned.

## Local check

```sh
python3 tools/sign/check_signed.py "C:\Games\TrueCombat Platinum"            # Windows: PowerShell verifies
python3 tools/sign/check_signed.py signed --unsigned-ref unsigned            # Linux: needs osslsigncode
```
