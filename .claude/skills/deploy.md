---
name: deploy
description: Commit, push to GitHub, pull to VPS, and deploy VectorForge to production
user_invocable: true
---

# Deploy VectorForge

Deploys to: **vf.aiosolibe.cloud** (VPS: 72.62.73.44)

## Step 1: Local checks

```bash
# Run tests
cd backend && python -m pytest tests/ -v --tb=short
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

If any fail, fix before deploying.

## Step 2: Git commit & push

```bash
cd "c:/Users/HP/My Drive (supportibe@gmail.com)/Raster-to-vector"
git add -A
git status
# Review changes, then commit:
git commit -m "<describe what changed>"
git push origin master
```

## Step 3: SSH to VPS and pull

```bash
ssh root@72.62.73.44 << 'REMOTE'
  cd /opt/vectorforge    # or wherever the repo is cloned
  git pull origin master

  # Install backend deps
  cd backend
  pip install -e ".[dev]"

  # Install potrace if not present
  which potrace || apt-get install -y potrace

  # Build frontend
  cd ../frontend
  npm ci
  npm run build

  # Restart services
  systemctl restart vectorforge-backend
  systemctl restart nginx

  # Verify
  curl -s http://localhost:8000/health
  echo "Deployed to vf.aiosolibe.cloud"
REMOTE
```

## Step 4: Verify production

```bash
curl -s https://vf.aiosolibe.cloud/health
curl -s https://vf.aiosolibe.cloud/api/conversions/analyze-colors \
  -F "file=@References/Outputs/Sample/owl_v8_transparent.png"
```

## First-time VPS setup

If this is the first deploy, run these setup steps on the VPS:

```bash
ssh root@72.62.73.44 << 'SETUP'
  # System deps
  apt-get update && apt-get install -y python3.12 python3.12-venv python3-pip nodejs npm potrace nginx certbot python3-certbot-nginx

  # Clone repo
  cd /opt
  git clone <GITHUB_URL> vectorforge
  cd vectorforge

  # Backend
  cd backend
  python3.12 -m venv .venv
  source .venv/bin/activate
  pip install -e .
  mkdir -p ../data/uploads ../data/results

  # Create .env
  cp ../.env.example ../.env
  # Edit .env: set SECRET_KEY, BASE_URL=https://vf.aiosolibe.cloud, CORS_ORIGINS=https://vf.aiosolibe.cloud

  # Frontend
  cd ../frontend
  npm ci && npm run build

  # Systemd service for backend
  cat > /etc/systemd/system/vectorforge-backend.service << 'SVC'
[Unit]
Description=VectorForge Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vectorforge/backend
Environment=PATH=/opt/vectorforge/backend/.venv/bin:/usr/bin
ExecStart=/opt/vectorforge/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC

  systemctl daemon-reload
  systemctl enable vectorforge-backend
  systemctl start vectorforge-backend

  # Nginx config
  cat > /etc/nginx/sites-available/vectorforge << 'NGX'
server {
    server_name vf.aiosolibe.cloud;

    root /opt/vectorforge/frontend/dist;
    index index.html;

    client_max_body_size 50M;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|svg|ico|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
NGX

  ln -sf /etc/nginx/sites-available/vectorforge /etc/nginx/sites-enabled/
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl restart nginx

  # SSL
  certbot --nginx -d vf.aiosolibe.cloud --non-interactive --agree-tos -m supportibe@gmail.com

  echo "First-time setup complete: https://vf.aiosolibe.cloud"
SETUP
```
