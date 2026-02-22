"""
Build script for creating a PyInstaller onedir distribution.
The output will be in dist/BeatSaberMapfileCreator/.
"""

import subprocess
import sys

def main():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "BeatSaberMapfileCreator.spec",
        "--noconfirm",
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    print("\nBuild complete! Output: dist/BeatSaberMapfileCreator/")

if __name__ == "__main__":
    main()
