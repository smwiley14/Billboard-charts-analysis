# Making the Dashboard Publicly Accessible

This guide will help you expose your Billboard Dashboard publicly so you can share a link (e.g., in your GitHub README).

## Options Overview

1. **Quick & Simple**: Direct port access (not recommended for production)
2. **Recommended**: Nginx reverse proxy with domain + SSL/HTTPS
3. **Alternative**: Cloudflare Tunnel (no port opening needed)

---

## Option 1: Quick Direct Access (Simple but Less Secure)

If you just need quick access without a domain:

### Steps:

1. **Open port 8501 in Digital Ocean Firewall**
   - Go to Digital Ocean → Networking → Firewalls
   - Add inbound rule: TCP port 8501, source: 0.0.0.0/0 (all IPs)

2. **Access via IP**
   - Your dashboard will be at: `http://YOUR_SERVER_IP:8501`
   - Example: `http://164.92.123.45:8501`

3. **Update Docker Compose** (if not already done)
   ```yaml
   # In docker-compose.yaml, dashboard service should have:
   ports:
     - "8501:8501"
   ```

**⚠️ Security Note**: This exposes your dashboard without encryption. Anyone with the IP can access it.

---

## Option 2: Nginx + Domain + SSL (Recommended for Production)

This gives you a clean URL like `https://dashboard.yourdomain.com` with HTTPS encryption.

### Prerequisites

- A domain name (you can get one cheap from Namecheap, Google Domains, etc.)
- DNS access to point your domain to your Digital Ocean server

### Step 1: Configure DNS

1. Add an A record in your domain's DNS settings:
   - **Type**: A
   - **Name**: `dashboard` (or `@` for root domain)
   - **Value**: Your Digital Ocean server IP
   - **TTL**: 3600 (or default)

2. Wait for DNS propagation (usually 5-30 minutes)
   - Check with: `nslookup dashboard.yourdomain.com`

### Step 2: Install Nginx

```bash
# On your Digital Ocean server
sudo apt update
sudo apt install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
```

### Step 3: Configure Nginx

```bash
# Create nginx configuration
sudo nano /etc/nginx/sites-available/billboard-dashboard
```

Paste this configuration (update `your-domain.com` with your actual domain):

```nginx
server {
    listen 80;
    server_name dashboard.your-domain.com;  # Change this!

    # Increase timeouts for long-running queries
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # WebSocket support
        proxy_buffering off;
    }
}
```

### Step 4: Enable the Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/billboard-dashboard /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

### Step 5: Set Up SSL with Let's Encrypt (Free HTTPS)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d dashboard.your-domain.com

# Certbot will:
# - Automatically configure SSL
# - Set up auto-renewal
# - Redirect HTTP to HTTPS
```

### Step 6: Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'
# Or manually:
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Optionally remove direct access to 8501
sudo ufw delete allow 8501/tcp
```

### Step 7: Update Nginx Config for SSL (Auto-done by certbot)

Certbot automatically updates your config, but if you want to do it manually:

```nginx
server {
    listen 80;
    server_name dashboard.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dashboard.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/dashboard.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dashboard.your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Increase timeouts for long-running queries
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_buffering off;
    }
}
```

### Done! 

Your dashboard is now accessible at: `https://dashboard.your-domain.com`

---

## Option 3: Cloudflare Tunnel (No Port Opening Needed)

If you don't want to open ports or set up Nginx, use Cloudflare Tunnel:

### Steps:

1. **Create Cloudflare account** (free) and add your domain
2. **Install cloudflared** on your server:
   ```bash
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared-linux-amd64.deb
   ```

3. **Create tunnel**:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create dashboard
   ```

4. **Configure tunnel**:
   ```bash
   # Edit config file
   sudo nano ~/.cloudflared/config.yml
   ```
   
   Add:
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: /home/$USER/.cloudflared/<tunnel-id>.json

   ingress:
     - hostname: dashboard.your-domain.com
       service: http://localhost:8501
     - service: http_status:404
   ```

5. **Run tunnel** (or set up as systemd service):
   ```bash
   cloudflared tunnel run dashboard
   ```

More details: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/

---

## Adding Password Protection (Optional)

To restrict access, add basic authentication to Nginx:

### Step 1: Create Password File

```bash
# Install apache2-utils if needed
sudo apt install apache2-utils -y

# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd username
# Enter password when prompted
```

### Step 2: Update Nginx Config

Add these lines inside the `location /` block:

```nginx
location / {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    # ... rest of proxy settings
}
```

### Step 3: Reload Nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Updating Your GitHub README

Once your dashboard is accessible, add a badge and link to your README:

```markdown
## 🎵 Live Dashboard

[![Dashboard](https://img.shields.io/badge/Dashboard-Live-brightgreen)](https://dashboard.your-domain.com)

View the interactive Billboard Charts Analysis Dashboard: [https://dashboard.your-domain.com](https://dashboard.your-domain.com)
```

Or use a more detailed badge:

```markdown
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dashboard.your-domain.com)
```

---

## Troubleshooting

### Can't access dashboard

1. **Check if dashboard is running**:
   ```bash
   docker compose ps dashboard
   ```

2. **Check if port is accessible**:
   ```bash
   curl http://localhost:8501
   ```

3. **Check Nginx status**:
   ```bash
   sudo systemctl status nginx
   sudo nginx -t
   ```

4. **Check firewall**:
   ```bash
   sudo ufw status
   ```

5. **Check DNS**:
   ```bash
   nslookup dashboard.your-domain.com
   ```

### SSL certificate issues

- Make sure DNS is pointing to your server before running certbot
- Check certificate: `sudo certbot certificates`
- Renew manually: `sudo certbot renew`

### WebSocket connection issues

Make sure your Nginx config includes:
```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

---

## Security Best Practices

1. ✅ Use HTTPS (SSL/TLS) - **Always use Option 2 or 3**
2. ✅ Keep your server updated: `sudo apt update && sudo apt upgrade`
3. ✅ Use a firewall (ufw is already configured in Digital Ocean)
4. ✅ Consider password protection if sensitive data
5. ✅ Monitor access logs: `sudo tail -f /var/log/nginx/access.log`
6. ⚠️ Don't expose database ports publicly
7. ⚠️ Keep dashboard dependencies updated

---

## Quick Reference Commands

```bash
# Nginx
sudo nginx -t                          # Test config
sudo systemctl reload nginx           # Reload config
sudo systemctl restart nginx          # Restart nginx
sudo tail -f /var/log/nginx/error.log # View errors

# Dashboard
docker compose logs -f dashboard       # View dashboard logs
docker compose restart dashboard       # Restart dashboard

# SSL
sudo certbot renew                     # Renew certificates
sudo certbot certificates              # List certificates

# Firewall
sudo ufw status                        # Check firewall
sudo ufw allow 443/tcp                 # Allow HTTPS
```

