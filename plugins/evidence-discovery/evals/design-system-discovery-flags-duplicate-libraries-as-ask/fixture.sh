#!/bin/bash
set -euo pipefail

cat > package.json <<'EOF'
{
  "name": "fixture-app",
  "dependencies": { "@fixture/ui": "^2.1.0", "@other/ui-kit": "^1.0.0" }
}
EOF

mkdir -p src/components
cat > src/components/Modal.tsx <<'EOF'
// in-repo modal component, duplicates @fixture/ui's Modal
export function Modal() {}
EOF
