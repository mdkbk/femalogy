#!/bin/bash
# One-time setup. Everything stays inside this folder:
#   .tools/node       -> portable Node.js (downloaded from nodejs.org, checksum-verified)
#   .tools/npm-cache  -> npm's download cache
#   node_modules/     -> the app's packages (exact versions from package-lock.json)
# To remove it all later: delete .tools and node_modules
set -e
cd "$(dirname "$0")"
TOOLS="$(pwd)/.tools"
NODE_LINE="latest-v24.x"

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  PLATFORM=darwin-arm64 ;;
  Darwin-x86_64) PLATFORM=darwin-x64 ;;
  Linux-x86_64)  PLATFORM=linux-x64 ;;
  Linux-aarch64) PLATFORM=linux-arm64 ;;
  *) echo "Unsupported system: $(uname -s) $(uname -m)"; exit 1 ;;
esac

mkdir -p "$TOOLS"
if [ ! -x "$TOOLS/node/bin/node" ]; then
  echo "==> Downloading Node.js into .tools/"
  BASE="https://nodejs.org/dist/$NODE_LINE"
  SUMS="$(curl -fsSL "$BASE/SHASUMS256.txt")"
  FILE="$(echo "$SUMS" | awk -v p="$PLATFORM" '$2 ~ "^node-v.*-" p "\\.tar\\.gz$" {print $2; exit}')"
  [ -n "$FILE" ] || { echo "Couldn't find a Node.js download for $PLATFORM"; exit 1; }
  curl -fsSL -o "$TOOLS/$FILE" "$BASE/$FILE"
  WANT="$(echo "$SUMS" | awk -v f="$FILE" '$2 == f {print $1}')"
  if command -v shasum >/dev/null; then GOT="$(shasum -a 256 "$TOOLS/$FILE" | awk '{print $1}')"
  else GOT="$(sha256sum "$TOOLS/$FILE" | awk '{print $1}')"; fi
  [ "$WANT" = "$GOT" ] || { echo "Checksum mismatch for $FILE, stopping."; rm -f "$TOOLS/$FILE"; exit 1; }
  rm -rf "$TOOLS/node" && mkdir -p "$TOOLS/node"
  tar -xzf "$TOOLS/$FILE" -C "$TOOLS/node" --strip-components=1
  rm -f "$TOOLS/$FILE"
fi

export PATH="$TOOLS/node/bin:$PATH"
export npm_config_cache="$TOOLS/npm-cache"
export npm_config_update_notifier=false
echo "==> Node $(node --version), installing packages"
npm ci --no-audit --no-fund

echo ""
echo "Done. Start the backend first (../femalogy-backend/run.sh), then:  ./run.sh"
