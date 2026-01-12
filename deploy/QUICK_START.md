# Quick Start Deployment Guide

## Fastest Way to Deploy

### Option A: Using Docker Compose (Easiest - Already Configured!)

If you're using docker-compose, the dashboard service is **already configured** in your `docker-compose.yaml` with the correct environment variables. Just start it:

```bash
# On your Digital Ocean server
cd /path/to/your/project

# Start the dashboard service
docker compose up -d dashboard

# Check it's running
docker compose ps dashboard

# View logs
docker compose logs -f dashboard
```

The dashboard will be available at: `http://YOUR_SERVER_IP:8501`

**Note**: The environment variables are already set in docker-compose.yaml, so no .env file needed!

---

### Option B: Systemd Service (For Non-Docker Deployment)

### 1. On Your Digital Ocean Server

```bash
# SSH into your server
ssh root@your-server-ip

# Clone or upload your project
git clone <your-repo> /opt/billboard-dashboard
# OR upload via SCP from your local machine:
# scp -r . root@your-server:/opt/billboard-dashboard

cd /opt/billboard-dashboard

# Create .env file with your database connection
nano .env
# Add: MUSIC_WAREHOUSE_DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/music_warehouse

# Run deployment
chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

### 2. Access Your Dashboard

Open in browser: `http://YOUR_SERVER_IP:8501`

---

## If Using Docker Compose

If you're using docker-compose (which you are!), the database connection is **already configured**:
- The dashboard service uses: `postgresql+psycopg2://airflow:airflow@postgres:5432/music_warehouse`
- `postgres` is the service name in your docker network
- No .env file needed - it's hardcoded in docker-compose.yaml

Just run: `docker compose up -d dashboard`

---

## If Your Database is on the Same Server (Non-Docker)

If your PostgreSQL database is running on the same Digital Ocean server but NOT in docker:

```bash
# Find your database connection details
# Your connection string might be:
MUSIC_WAREHOUSE_DATABASE_URL=postgresql+psycopg2://airflow:airflow@localhost:5432/music_warehouse
```

---

## If Your Database is on a Different Server

```bash
# Your connection string should point to the remote database:
MUSIC_WAREHOUSE_DATABASE_URL=postgresql+psycopg2://user:password@database-server-ip:5432/music_warehouse

# Make sure:
# 1. Database firewall allows connections from your dashboard server
# 2. PostgreSQL is configured to accept remote connections (pg_hba.conf)
```

---

## Quick Commands

```bash
# View logs
sudo journalctl -u billboard-dashboard -f

# Restart
sudo systemctl restart billboard-dashboard

# Stop
sudo systemctl stop billboard-dashboard

# Check status
sudo systemctl status billboard-dashboard
```

---

## Troubleshooting

**Dashboard won't start?**
```bash
sudo journalctl -u billboard-dashboard -n 50
```

**Can't connect to database?**
- Test connection: `psql -h HOST -U USER -d music_warehouse`
- Check if database is running
- Verify firewall rules

**Port already in use?**
```bash
# Find what's using port 8501
sudo lsof -i :8501
# Kill it or change port in dashboard.service
```

