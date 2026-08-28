# Radeon Pro V620 Linux Power-Cap Workaround

A V620-specific toolkit for lowering the Linux `amdgpu` power-cap floor and then setting a persistent custom power cap through the normal hwmon interface.

This repository packages a workaround validated on an AMD Radeon Pro V620 (Navi 21, PCI device `1002:73a1`, subsystem `1002:0e34`) whose stock host-visible PPT range was fixed at 250 W / 250 W.

## What was verified

On the original test V620:

- stock host-visible PPT range: **250 W minimum / 250 W maximum**;
- patched host-visible PPT range: **175 W minimum / 250 W maximum**;
- writing `175000000` µW to the dynamically discovered `power1_cap` node succeeded;
- the active socket power limit then reported **175 W**;
- the firmware maximum remained **250 W**.

The kernel change only lowers the driver's cached `smu->min_power_limit`. It does **not** raise `smu->max_power_limit`.

## Important limitation

This is a **lower-power-cap workaround**, not an above-stock overclocking unlock.

You can choose a different driver-visible minimum at patch time, then use `v620-powercap set <watts>` for values in the range the patched driver and card firmware accept.

The firmware/SMU can still reject a requested value. The only below-stock value validated on the original card was **175 W**. Lower values are experimental.

## Why it works

The generic `amdgpu` SMU path rejects requests outside the cached minimum/maximum range before calling the existing card-specific power-limit setter. The tested V620 reported both ends as 250 W, but accepted 175 W once the driver's cached minimum was lowered.

This is the same general class of workaround used for Navi/RDNA cards when the Linux-side minimum-power-cap guard is more restrictive than the hardware path. A broader example is OpenMandriva's `amdgpu-ignore-min-pcap` patch. This repository deliberately narrows the modification to the exact V620 PCI IDs.

## Repository layout

```text
scripts/
  patch-v620-ppt.py      patch a Linux kernel tree with a chosen V620 minimum
  v620-powercap          auto-detect V620 + amdgpu hwmon and get/set the cap
  install.sh             install the runtime helper + optional boot service
  uninstall.sh           remove installed runtime/service files

systemd/
  v620-powercap.service.in

docs/
  KERNEL-BUILD.md
  TECHNICAL-NOTES.md

v620-powercap.conf.example
```

No author home directory, PCI bus address, `hwmonN` number, kernel version, or kernel build directory is hard-coded.

## 1. Check that the card matches

```bash
./scripts/v620-powercap detect
./scripts/v620-powercap status
```

The helper matches:

```text
vendor            0x1002
device            0x73a1
subsystem_vendor  0x1002
subsystem_device  0x0e34
```

If more than one matching V620 is installed:

```bash
./scripts/v620-powercap --pci 0000:53:00.0 status
```

## 2. Patch a kernel source tree

Obtain the source tree for the kernel you intend to build, then run:

```bash
./scripts/patch-v620-ppt.py /path/to/linux-source --min-w 175
```

The patcher:

- locates `drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c` relative to the supplied kernel tree;
- searches for the `smu_get_asic_power_limits()` initialization block instead of relying on a line number;
- refuses to modify the file if the expected block is absent or ambiguous;
- applies the change only to the exact V620 PCI IDs;
- only lowers the cached minimum when the configured value is below the firmware-reported minimum;
- preserves current/default/maximum firmware values;
- saves a stock backup before writing.

Preview without modifying anything:

```bash
./scripts/patch-v620-ppt.py /path/to/linux-source --min-w 175 --dry-run
```

Check an already-patched tree:

```bash
./scripts/patch-v620-ppt.py /path/to/linux-source --check
```

Revert from the saved backup:

```bash
./scripts/patch-v620-ppt.py /path/to/linux-source --revert
```

Build/install the modified kernel using your distribution's normal procedure. See [`docs/KERNEL-BUILD.md`](docs/KERNEL-BUILD.md).

## 3. Set a custom runtime cap

After booting the patched kernel:

```bash
sudo ./scripts/v620-powercap set 175
```

or another value within the exposed/accepted range:

```bash
sudo ./scripts/v620-powercap set 200
```

Status:

```bash
./scripts/v620-powercap status
```

The helper discovers both the V620 PCI function and its current `amdgpu` hwmon directory dynamically, so `hwmon5` becoming `hwmon7` after reboot does not matter.

## 4. Make the chosen cap persistent

```bash
sudo ./scripts/install.sh --watts 175
```

This creates a config and systemd oneshot service that waits for the V620 hwmon interface and reapplies the cap after boot.

Default locations:

```text
/usr/local/sbin/v620-powercap
/etc/v620-powercap.conf
/etc/systemd/system/v620-powercap.service
```

These are configurable defaults rather than dependencies on one machine's layout:

```bash
sudo BIN_DIR=/opt/v620/bin \
     SYSTEMD_DIR=/etc/systemd/system \
     CONFIG_FILE=/etc/v620-powercap.conf \
     ./scripts/install.sh --watts 175
```

Change the persistent cap later:

```bash
sudoedit /etc/v620-powercap.conf
sudo systemctl restart v620-powercap.service
```

Example config:

```bash
POWER_CAP_W=175
# V620_PCI=0000:53:00.0
```

Leave `V620_PCI` unset when there is only one matching card.

## Safety / recovery

1. Keep a known-good stock kernel installed and bootable.
2. Do not overwrite your only working kernel.
3. Start close to stock and move downward gradually.
4. Validate sustained load, clocks, temperatures and errors.
5. If the firmware rejects a value, do not assume bypassing more checks is safe.
6. This repository intentionally does not provide an above-stock maximum-power bypass.

## Tested platform

```text
AMD Radeon Pro V620 32 GB
Navi 21 / gfx1030
PCI device: 1002:73a1
Subsystem: 1002:0e34
Linux amdgpu
Ubuntu 26.04
Linux 7.0.0-based source
```

The original machine-specific path names, PCI BDF and `hwmonN` index have intentionally been removed from the public tooling.

## References / acknowledgement

- Linux `amdgpu_smu.c` generic SMU power-limit path:
  https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c
- OpenMandriva's broader `amdgpu-ignore-min-pcap` approach:
  https://github.com/OpenMandrivaAssociation/kernel/blob/master/amdgpu-ignore-min-pcap.patch

## License

GPL-2.0-only. See [`LICENSE`](LICENSE).
