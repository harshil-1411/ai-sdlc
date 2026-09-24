#!/bin/bash
set -euo pipefail

cat > package.json <<'EOF'
{ "name": "fixture-app", "dependencies": { "@fixture/ui": "^2.1.0" } }
EOF

mkdir -p src/components
cat > src/components/README.md <<'EOF'
Storybook docs for @fixture/ui live at http://localhost:6006
EOF

cat > tokens.json <<'EOF'
{ "color": { "primary": "#1a73e8" }, "spacing": { "unit": 8 } }
EOF
