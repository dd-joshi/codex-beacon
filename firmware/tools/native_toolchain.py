"""Make the declared MinGW compiler available to PlatformIO native tests."""

from pathlib import Path

Import("env")  # type: ignore[name-defined]

package_dir = env.PioPlatform().get_package_dir("toolchain-gccmingw32")  # type: ignore[name-defined]
if package_dir:
    env.PrependENVPath("PATH", str(Path(package_dir) / "bin"))  # type: ignore[name-defined]
    env.Append(  # type: ignore[name-defined]
        LINKFLAGS=["-static", "-static-libgcc", "-static-libstdc++"]
    )
