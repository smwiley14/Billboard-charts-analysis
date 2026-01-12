# Fix: psycopg2 Module Not Found

## Quick Fix

The dashboard container needs to be rebuilt with the updated dependencies. Here's how:

### Option 1: Rebuild the Dashboard Container (Recommended)

```bash
# Stop the dashboard container
docker compose stop dashboard

# Rebuild the dashboard image
docker compose build dashboard

# Start it again
docker compose up -d dashboard

# Check logs to verify it's working
docker compose logs -f dashboard
```

### Option 2: Install psycopg2-binary in Running Container (Temporary Fix)

If you need a quick fix without rebuilding:

```bash
# Enter the running container
docker compose exec dashboard bash

# Install psycopg2-binary
pip install psycopg2-binary

# Exit the container
exit

# Restart the dashboard
docker compose restart dashboard
```

**Note**: This temporary fix will be lost if you rebuild the container. Use Option 1 for a permanent fix.

---

## What Changed

1. **Updated `requirements.txt`**: Changed `psycopg2` to `psycopg2-binary>=2.9.0`
   - `psycopg2-binary` is pre-compiled and doesn't require build tools
   - Easier to install and more reliable

2. **Updated `Dockerfile.dashboard`**: Added `libpq-dev` and `python3-dev`
   - These are needed if you want to use `psycopg2` (non-binary version)
   - Not strictly needed for `psycopg2-binary`, but good to have

---

## Verify It's Working

After rebuilding, check the dashboard logs:

```bash
docker compose logs dashboard | grep -i "error\|psycopg\|database"
```

You should see the dashboard starting without psycopg2 errors. The dashboard should be accessible at `http://YOUR_SERVER_IP:8501`.

