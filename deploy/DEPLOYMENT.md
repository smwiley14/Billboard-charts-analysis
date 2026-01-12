# Billboard Dashboard Deployment Guide

This guide covers multiple deployment options for the Billboard Charts Analysis Dashboard on Digital Ocean.

## Prerequisites

- Digital Ocean server with:
  - PostgreSQL database running (your existing setup)
  - Airflow running (your existing setup)
  - Python 3.9+ installed
  - Root/sudo access

## Option 1: Systemd Service (Recommended for Simple Deployment)

This is the simplest production-ready option. The dashboard runs as a systemd service that automatically restarts on failure.

### Steps:

1. **SSH into your Digital Ocean server**

2. **Clone or upload your project files**
   ```bash
   # If using git
   git clone <your-repo-url> /opt/billboard-dashboard
   cd /opt/billboard-dashboard
   
   # Or upload files via SCP
   # scp -r . user@your-server:/opt/billboard-dashboard
   ```

3. **Create `.env` file with database connection**
   ```bash
   cd /opt/billboard-dashboard
   nano .env
   ```
   
   Add your database URL:
   ```env
   MUSIC_WAREHOUSE_DATABASE_URL=postgresql+psycopg2://username:password@host:5432/music_warehouse
   ```
   
   **Important**: Replace with your actual database credentials. If your database is on the same server:
   - `host` might be `localhost` or `127.0.0.1`
   - `port` is usually `5432`
   - `username` and `password` are your PostgreSQL credentials
   - `music_warehouse` is your database name

4. **Run the deployment script**
   ```bash
   chmod +x deploy/deploy.sh
   sudo ./deploy/deploy.sh
   ```

5. **Verify it's running**
   ```bash
   sudo systemctl status billboard-dashboard
   ```

6. **Access the dashboard**
   - Direct access: `http://YOUR_SERVER_IP:8501`
   - Check your server IP: `hostname -I`

### Managing the Service

```bash
# View logs
sudo journalctl -u billboard-dashboard -f

# Restart
sudo systemctl restart billboard-dashboard

# Stop
sudo systemctl stop billboard-dashboard

# Start
sudo systemctl start billboard-dashboard

# Check status
sudo systemctl status billboard-dashboard
```

---

## Option 2: Docker Deployment

If you prefer containerization, you can run the dashboard in Docker.

### Steps:

1. **Build the Docker image**
   ```bash
   docker build -f deploy/Dockerfile.dashboard -t billboard-dashboard .
   ```

2. **Create `.env` file** (same as Option 1)

3. **Run the container**
   ```bash
   docker run -d \
     --name billboard-dashboard \
     -p 8501:8501 \
     --env-file .env \
     --restart unless-stopped \
     billboard-dashboard
   ```

4. **Verify**
   ```bash
   docker ps
   docker logs billboard-dashboard
   ```

5. **Access**: `http://YOUR_SERVER_IP:8501`

### Docker Compose Option

You can also add the dashboard to your existing `docker-compose.yaml`:

```yaml
  dashboard:
    build:
      context: .
      dockerfile: deploy/Dockerfile.dashboard
    ports:
      - "8501:8501"
    env_file:
      - .env
    environment:
      - MUSIC_WAREHOUSE_DATABASE_URL=${MUSIC_WAREHOUSE_DATABASE_URL}
    depends_on:
      - postgres
    restart: unless-stopped
```

Then run: `docker compose up -d dashboard`

---

## Option 3: Nginx Reverse Proxy (Recommended for Production)

This adds SSL/HTTPS support and better security. Use this with Option 1 or 2.

### Steps:

1. **Install Nginx** (if not already installed)
   ```bash
   sudo apt update
   sudo apt install nginx
   ```

2. **Configure Nginx**
   ```bash
   sudo cp deploy/nginx.conf /etc/nginx/sites-available/billboard-dashboard
   sudo nano /etc/nginx/sites-available/billboard-dashboard
   ```
   
   Edit the `server_name` line to match your domain or IP.

3. **Enable the site**
   ```bash
   sudo ln -s /etc/nginx/sites-available/billboard-dashboard /etc/nginx/sites-enabled/
   sudo nginx -t  # Test configuration
   sudo systemctl reload nginx
   ```

4. **Set up SSL with Let's Encrypt** (optional but recommended)
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

5. **Access**: `http://your-domain.com` or `https://your-domain.com` (if SSL configured)

---

## Option 4: Digital Ocean App Platform (Managed Service)

For a fully managed solution:

1. Go to Digital Ocean App Platform
2. Create a new app
3. Connect your GitHub repository
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `streamlit run dashboard.py --server.port 8080 --server.address 0.0.0.0`
   - **Environment Variables**: Add `MUSIC_WAREHOUSE_DATABASE_URL`
5. Deploy

**Note**: You'll need to ensure your database is accessible from App Platform (may require firewall rules or a managed database).

---

## Security Considerations

1. **Firewall**: Only expose port 8501 if needed, or use Nginx
   ```bash
   # Allow only specific IPs
   sudo ufw allow from YOUR_IP to any port 8501
   
   # Or use Nginx with authentication
   ```

2. **Database Access**: Ensure your database firewall allows connections from the dashboard server

3. **Environment Variables**: Never commit `.env` files. Use secrets management in production

4. **HTTPS**: Always use HTTPS in production (use Let's Encrypt with Nginx)

---

## Troubleshooting

### Dashboard won't start
- Check logs: `sudo journalctl -u billboard-dashboard -n 50`
- Verify database connection: Test the connection string manually
- Check port availability: `sudo netstat -tulpn | grep 8501`

### Can't connect to database
- Verify database is running: `sudo systemctl status postgresql` (or check Docker)
- Test connection: `psql -h HOST -U USERNAME -d music_warehouse`
- Check firewall rules on database server
- Verify connection string format in `.env`

### Performance issues
- Increase Streamlit resources in `dashboard.service`:
  ```ini
  Environment="STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200"
  Environment="STREAMLIT_SERVER_MAX_MESSAGE_SIZE=200"
  ```
- Consider adding caching (already implemented in dashboard.py)
- Monitor database query performance

---

## Updating the Dashboard

1. **Pull latest changes** (if using git)
   ```bash
   cd /opt/billboard-dashboard
   git pull
   ```

2. **Update dependencies** (if requirements.txt changed)
   ```bash
   /opt/billboard-dashboard/venv/bin/pip install -r requirements.txt
   ```

3. **Restart service**
   ```bash
   sudo systemctl restart billboard-dashboard
   ```

---

## Monitoring

Consider setting up monitoring:

1. **Uptime monitoring**: Use services like UptimeRobot or Pingdom
2. **Log aggregation**: Use `journalctl` or forward logs to a service
3. **Resource monitoring**: Monitor CPU/memory usage
   ```bash
   htop
   # or
   docker stats billboard-dashboard
   ```

---

## Need Help?

- Check Streamlit logs: `sudo journalctl -u billboard-dashboard -f`
- Check database connectivity
- Verify environment variables are set correctly
- Review firewall and network settings

