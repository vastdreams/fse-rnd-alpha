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
