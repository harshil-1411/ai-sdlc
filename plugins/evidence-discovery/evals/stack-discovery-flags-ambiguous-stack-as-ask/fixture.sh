#!/bin/bash
set -euo pipefail

cat > package.json <<'EOF'
{ "name": "fixture-app", "dependencies": { "express": "^4.19.0" } }
EOF

mkdir -p src
cat > src/server.js <<'EOF'
const express = require('express');
module.exports = express();
EOF

cat > requirements.txt <<'EOF'
Django==4.2
psycopg2==2.9
EOF

mkdir -p app
cat > app/views.py <<'EOF'
from django.http import HttpResponse

def index(request):
    return HttpResponse("ok")
EOF
