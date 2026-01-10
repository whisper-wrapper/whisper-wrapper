#!/bin/bash
# Build script for Whisper GUI Wrapper DEB package

set -e

# Metadata (single source of truth in src/meta.py)
APP_NAME="$(python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))
from meta import APP_NAME
print(APP_NAME)
PY
)"
VERSION="$(python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))
from meta import APP_VERSION
print(APP_VERSION)
PY
)"
ARCH="${ARCH:-}"
if [ -z "${ARCH}" ]; then
    if command -v dpkg >/dev/null 2>&1; then
        ARCH="$(dpkg --print-architecture)"
    else
        case "$(uname -m)" in
            x86_64) ARCH="amd64" ;;
            aarch64|arm64) ARCH="arm64" ;;
            *) ARCH="amd64" ;;
        esac
    fi
fi
MAINTAINER_NAME="${MAINTAINER_NAME:-Whisper Wrapper Maintainers}"
MAINTAINER_EMAIL="${MAINTAINER_EMAIL:-maintainers@example.com}"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
DIST_DIR="${SCRIPT_DIR}/dist"
DEB_DIR="${BUILD_DIR}/deb_dist"

echo "Building ${APP_NAME} v${VERSION}"
echo "================================"

# Enforce architecture guideline: abort if any source file exceeds 250 lines
echo "Checking source file line limits..."
python3 - <<'PY'
import sys
from pathlib import Path

MAX_LINES = 250
too_long = []
for path in Path("src").rglob("*.py"):
    line_count = sum(1 for _ in path.open(encoding="utf-8"))
    if line_count > MAX_LINES:
        too_long.append((path, line_count))

if too_long:
    print("ERROR: Source files exceed line limit (250 lines):")
    for path, count in too_long:
        print(f"  {path}: {count} lines")
    sys.exit(1)
PY

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

# Check for virtual environment
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "${SCRIPT_DIR}/venv"
fi

# Activate venv and install dependencies
echo "Installing dependencies..."
source "${SCRIPT_DIR}/venv/bin/activate"
pip install --upgrade pip
pip install -r "${SCRIPT_DIR}/requirements.txt"
pip install pyinstaller

# Build with PyInstaller
echo "Building with PyInstaller..."
cd "${SCRIPT_DIR}"

pyinstaller --clean --noconfirm --onedir --windowed \
    --name "${APP_NAME}" \
    --distpath "${DIST_DIR}" \
    --workpath "${BUILD_DIR}/pyinstaller" \
    --specpath "${BUILD_DIR}" \
    --hidden-import="pynput.keyboard._xorg" \
    --hidden-import="pynput.mouse._xorg" \
    --collect-all="faster_whisper" \
    --collect-submodules="sounddevice" \
    --collect-submodules="webrtcvad" \
    src/app/__main__.py

# Build trigger.py separately (smaller binary for hotkey)
echo "Building trigger..."
pyinstaller --clean --noconfirm --onefile \
    --name "whisper-trigger" \
    --distpath "${DIST_DIR}" \
    --workpath "${BUILD_DIR}/pyinstaller" \
    --specpath "${BUILD_DIR}" \
    trigger.py

# Prepare DEB structure
echo "Preparing DEB package structure..."
mkdir -p "${DEB_DIR}/DEBIAN"
mkdir -p "${DEB_DIR}/opt/${APP_NAME}"
mkdir -p "${DEB_DIR}/usr/bin"
mkdir -p "${DEB_DIR}/usr/share/applications"
mkdir -p "${DEB_DIR}/usr/share/doc/${APP_NAME}"

# Copy files
cp -r "${DIST_DIR}/${APP_NAME}"/* "${DEB_DIR}/opt/${APP_NAME}/"
cp "${DIST_DIR}/whisper-trigger" "${DEB_DIR}/opt/${APP_NAME}/"
cp "${SCRIPT_DIR}/LICENSE" "${DEB_DIR}/usr/share/doc/${APP_NAME}/LICENSE"
cp "${SCRIPT_DIR}/NOTICE" "${DEB_DIR}/usr/share/doc/${APP_NAME}/NOTICE"

# Create symlinks
ln -sf "/opt/${APP_NAME}/${APP_NAME}" "${DEB_DIR}/usr/bin/${APP_NAME}"
ln -sf "/opt/${APP_NAME}/whisper-trigger" "${DEB_DIR}/usr/bin/whisper-trigger"

# Create .desktop file
cat > "${DEB_DIR}/usr/share/applications/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Whisper Wrapper
Comment=Voice-to-text input using Whisper
Exec=/opt/${APP_NAME}/${APP_NAME}
Icon=audio-input-microphone
Terminal=false
Categories=Utility;Accessibility;Audio;
Keywords=voice;speech;transcription;whisper;
StartupNotify=false
EOF

# Create control file
cat > "${DEB_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: libportaudio2, ffmpeg, libxcb-cursor0
Maintainer: ${MAINTAINER_NAME} <${MAINTAINER_EMAIL}>
Description: Voice-to-text input using OpenAI Whisper
 A GUI application for voice input that uses the Whisper
 speech recognition model to transcribe audio and inject
 text into the active window. Supports both X11 and Wayland.
EOF

# Create postinst script
cat > "${DEB_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Make binaries executable
chmod +x /opt/whisper-wrapper/whisper-wrapper
chmod +x /opt/whisper-wrapper/whisper-trigger

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

echo ""
echo "Whisper Wrapper installed successfully!"
echo ""
echo "Usage:"
echo "  - Launch from application menu or run: whisper-wrapper"
echo "  - Default hotkey (X11): Ctrl+Alt+R"
echo "  - For Wayland: bind 'whisper-trigger toggle' to a system hotkey"
echo ""
EOF
chmod +x "${DEB_DIR}/DEBIAN/postinst"

# Create postrm script
cat > "${DEB_DIR}/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

if [ "$1" = "purge" ]; then
    # Remove config directory
    rm -rf ~/.config/whisper-wrapper 2>/dev/null || true
    rm -rf ~/.cache/whisper-wrapper 2>/dev/null || true
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi
EOF
chmod +x "${DEB_DIR}/DEBIAN/postrm"

# Build DEB package
echo "Building DEB package..."
DEB_FILE="${DIST_DIR}/${APP_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build "${DEB_DIR}" "${DEB_FILE}"

# Verify package
echo ""
echo "Verifying package..."
dpkg-deb --info "${DEB_FILE}"

echo ""
echo "================================"
echo "Build complete!"
echo "DEB package: ${DEB_FILE}"
echo ""
echo "Install with: sudo dpkg -i ${DEB_FILE}"
echo "Or: sudo apt install ./${DEB_FILE}"
