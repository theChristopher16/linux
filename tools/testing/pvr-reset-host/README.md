# PowerVR reset power-reference host regression fixture

Review support for `fix/pvr-reset-power-reference`. These files live only on
this fork's test branch; they are not proposed as kernel build inputs.

The runner extracts the actual `pvr_power_get_clear()` and `pvr_power_reset()`
functions from two supplied source files. It compiles each with single-threaded
synthetic callbacks and runs 17 scenarios at `-O2` and with ASan/UBSan at `-O1`,
using `-Wall -Wextra -Werror`.

## Reproduce

Download this directory's `run.py` and `fixture.c.in` together. Obtain the exact
public source files:

- [Baseline pvr_power.c](https://raw.githubusercontent.com/OrchardLinux/linux/df7c930f80abd32a054617cd30ea450b7acfb3e0/drivers/gpu/drm/imagination/pvr_power.c), saved as `baseline-pvr_power.c`.
- [Candidate pvr_power.c](https://raw.githubusercontent.com/theChristopher16/linux/4ba2e4f6fd2fdd6a2cd84fd36542fb02cf32c7ef/drivers/gpu/drm/imagination/pvr_power.c), saved as `candidate-pvr_power.c`.

With Python 3 and Clang plus its sanitizer runtime:

```sh
python3 -I -B run.py --baseline baseline-pvr_power.c --candidate candidate-pvr_power.c
```

The runner performs no network requests or device access. Compiled files are
temporary and removed when it exits. It prints source/function hashes and the
result for each version and compiler mode. The baseline deliberately checks
the old behavior, including its unmatched power-reference release; "pass" for
that version means the bug was reproduced.

Expected SHA-256 values:

- Baseline: `a7b2aff2e44303188e21f0213f92b3243fc354fcc81072505314a101e06d0242`
- Candidate: `746363e9e246587067a434a9147c2c646603a5b9547f9c876671b436098a1386`

## Coverage and limits

Six cases cover soft/hard reset after failed PM-error clearing or a failed
second power acquisition (EIO or timeout). The candidate returns the error
without reset-body callbacks or an unmatched put. Other cases cover normal
soft/hard reset, successful PM recovery, an already-lost device, soft-to-hard
fallback, four later failure sites, and the existing ignored suspend error.

The PM acquisition/recovery helper may itself perform real PM work in the
kernel; the stub does not model that work. Locking, IRQ handling, firmware,
DRM unplug/SRCU, DMA, concurrency and hardware are not emulated. A passing
fixture does not prove recovery on any device or working GPU acceleration.
The early return leaves `lost` unchanged; caller/device-lifecycle policy
still needs review.

The fixture and runner are GPL-2.0-only OR MIT. The extracted public kernel
functions retain their original Imagination Technologies authorship/license.
