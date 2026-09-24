#!/bin/bash
set -euo pipefail

cat > CLAUDE.md <<'EOF'
# Project notes
This project uses Django (Python) with PostgreSQL for the backend.
EOF

cat > package.json <<'EOF'
{
  "name": "fixture-app",
  "dependencies": { "express": "^4.19.0" }
}
EOF

mkdir -p src
cat > src/server.js <<'EOF'
const express = require('express');
const app = express();
app.get('/health', (req, res) => res.send('ok'));
module.exports = app;
EOF
