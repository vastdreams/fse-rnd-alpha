# Deployment Guide

## Docker (Recommended)

```bash
cd deploy
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- FastAPI backend
- React frontend (via nginx)

Access at `http://localhost`

## Environment Variables

Copy `.env.example` to `.env` and set:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/rd_alpha
FMP_API_KEY=your_fmp_api_key
```

## Manual Deployment

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run build
# Serve dist/ with nginx or similar
```

### Frontend (Production note - `deploy/` stack)

If you are using the production Docker stack in `deploy/docker-compose.yml`, the nginx container serves static files from a bind mount:

- `deploy/frontend/dist` → `/usr/share/nginx/html`

That means copying files to `frontend/dist` **on the server** will not update the live site unless you also copy them into `deploy/frontend/dist`.

**Recommended:** use the deploy script:

```bash
./deploy/deploy.sh --deploy
```

**If you need frontend-only updates on EC2:**

```bash
# (run on your local machine)
cd frontend && npm run build && cd ..

# copy built assets into the *deploy-mounted* directory on the server
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip "mkdir -p /home/ubuntu/fse-rnd-alpha/deploy/frontend/dist"
scp -i ~/.ssh/your-key.pem -r frontend/dist/* ubuntu@your-ec2-ip:/home/ubuntu/fse-rnd-alpha/deploy/frontend/dist/

# restart nginx container
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip "cd /home/ubuntu/fse-rnd-alpha/deploy && docker compose restart frontend"
```

## AWS EC2

```bash
# Set environment variables
export EC2_HOST=your-ec2-ip
export KEY_PATH=~/.ssh/your-key.pem

# Deploy
./deploy/deploy.sh --deploy
```

## Health Checks

- Backend: `GET /health`
- API docs: `GET /docs`
