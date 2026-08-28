# Technical Notes

## Observed V620 behavior

The validated Radeon Pro V620 identified as:

```text
vendor            0x1002
device            0x73a1
subsystem_vendor  0x1002
subsystem_device  0x0e34
```

The stock driver populated a host-visible minimum and maximum of 250 W. The generic SMU setter rejects a request that falls outside the cached `smu->min_power_limit` / `smu->max_power_limit` range before the existing card-specific `set_power_limit` callback is reached.

## Narrow workaround

The patch is inserted immediately after the successful `smu_get_asic_power_limits()` call that populates current/default/max/min.

For the exact V620 PCI IDs, it lowers only the cached minimum when the configured value is lower than the firmware-reported minimum and no higher than the firmware-reported maximum.

Conceptually:

```c
if (exact_v620 &&
    smu->min_power_limit > configured_min &&
    smu->max_power_limit >= configured_min)
        smu->min_power_limit = configured_min;
```

Current/default/max remain untouched.

## Why the runtime helper writes hwmon directly

On the validated system, AMD SMI displayed the newly exposed 175–250 W range but its CLI rejected `175` as an input parameter. Writing the same target through the standard `amdgpu` hwmon `power1_cap` node succeeded:

```text
250000000 -> 175000000 uW
```

The active socket limit then reported 175 W.

The helper therefore writes `power1_cap` directly and verifies the result by reading it back.

## Dynamic discovery

Linux hwmon indices are not stable identifiers. The helper therefore:

1. searches `/sys/bus/pci/devices/*`;
2. matches the exact V620 PCI IDs;
3. searches that PCI function's `hwmon/hwmon*` children;
4. selects the child whose `name` is `amdgpu`;
5. reads/writes that device's `power1_cap`.

A PCI BDF can be supplied explicitly only when needed to disambiguate multiple matching cards.

## Relationship to broader Navi/RDNA workarounds

Some Linux projects/distributions carry patches that bypass the software-side minimum power-cap guard for AMD GPUs. OpenMandriva, for example, carries an `amdgpu-ignore-min-pcap` patch with an opt-in module parameter.

This project's default patch is deliberately narrower: it changes the cached minimum only for the exact Radeon Pro V620 PCI identity and never raises or bypasses the firmware maximum.
