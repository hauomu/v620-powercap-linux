# Building and Booting a Patched Kernel

The source patch changes `amdgpu`, so the modified driver must be built and loaded.

The exact kernel build commands differ by distribution. This repository deliberately does not hard-code an Ubuntu release, kernel ABI, source directory or output directory.

## Safe workflow

1. Keep your distribution's stock kernel installed and bootable.
2. Obtain the exact source used for the kernel you intend to modify.
3. Copy/build in a separate working directory.
4. Apply the V620 patch:

   ```bash
   ./scripts/patch-v620-ppt.py /path/to/linux-source --min-w 175
   ```

5. Review the generated change:

   ```bash
   diff -u \
     /path/to/linux-source/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c.v620-ppt-stock \
     /path/to/linux-source/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c
   ```

6. Build the kernel using your distribution's official packaging/build procedure.
7. Install the custom kernel alongside the stock kernel rather than replacing it.
8. Reboot into the custom kernel.
9. Confirm the driver-visible range:

   ```bash
   ./scripts/v620-powercap status
   ```

10. Set a conservative cap and validate stability.

## Original Ubuntu validation

The original test used Ubuntu 26.04 source based on Linux `7.0.0-29.29` and a separately named custom test ABI. The built `amdgpu` module contained the V620 override and the machine booted the custom kernel successfully.

Those exact package names and ABI numbers are intentionally not scripted here because they are distribution-specific and will become stale.

## Secure Boot

A locally built kernel/module may require signing or Secure Boot configuration where Secure Boot is enforced. Follow your distribution's documentation rather than disabling security features blindly.
