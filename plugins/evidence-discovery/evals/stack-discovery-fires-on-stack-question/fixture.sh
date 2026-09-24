#!/bin/bash
set -euo pipefail

cat > package.json <<'EOF'
{
  "name": "fixture-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.19.0",
    "pg": "^8.11.0",
    "mongoose": "^8.2.0"
  },
  "devDependencies": {
    "vitest": "^1.4.0"
  },
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "lint": "eslint ."
  }
}
EOF

cat > package-lock.json <<'EOF'
{ "name": "fixture-app", "lockfileVersion": 3 }
EOF

mkdir -p src/db
cat > src/server.js <<'EOF'
const express = require('express');
const app = express();
app.get('/health', (req, res) => res.send('ok'));
module.exports = app;
EOF

cat > src/db/pool.js <<'EOF'
const { Pool } = require('pg');
module.exports = new Pool();
EOF
