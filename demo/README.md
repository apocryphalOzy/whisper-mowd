# Whisper MOWD Demo

A simplified demo version of Whisper MOWD for market validation and testing.

## Features

- Audio file transcription using OpenAI Whisper
- Simple web interface
- Rate limiting (10 uploads/day per IP)
- Automatic file cleanup (24 hours)
- Zero-cost deployment ready

## Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements-demo.txt
   ```

2. **Run the application:**
   ```bash
   uvicorn app_demo:app --reload
   ```

3. **Access at:** http://localhost:8000

### Docker Deployment

1. **Using docker-compose:**
   ```bash
   docker-compose up -d
   ```

2. **Using the deploy script:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

## Configuration

Set environment variables in `.env` or docker-compose:

- `DEMO_PASSWORD`: Password for demo access (default: whisper2025)
- `WHISPER_MODEL`: Model size - tiny or base (default: tiny)
- `MAX_UPLOADS_PER_IP`: Daily upload limit (default: 10)
- `MAX_FILE_SIZE`: Maximum file size in bytes (default: 50MB)

## VPS Deployment

### Oracle Cloud Free Tier (Recommended)

1. **Create VM instance:**
   - Shape: VM.Standard.A1.Flex (ARM)
   - OCPU: 4
   - Memory: 24 GB
   - OS: Ubuntu 22.04

2. **Install Docker:**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker ubuntu
   ```

3. **Clone and deploy:**
   ```bash
   git clone https://github.com/your-repo/whisper-demo
   cd whisper-demo/demo
   ./deploy.sh
   ```

4. **Configure firewall:**
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
   sudo netfilter-persistent save
   ```

### SSL with Let's Encrypt

1. **Point domain to server IP**

2. **Install Certbot:**
   ```bash
   sudo snap install --classic certbot
   ```

3. **Get certificate:**
   ```bash
   sudo certbot certonly --standalone -d your-domain.com
   ```

4. **Update nginx.conf and restart**

## API Endpoints

- `GET /` - Web interface
- `POST /auth` - Authenticate with demo password
- `POST /upload` - Upload audio file
- `GET /status/{job_id}` - Check processing status
- `GET /result/{job_id}` - Get transcription result
- `GET /health` - Health check

## Demo Constraints

- **File size**: Max 50MB
- **Duration**: Max 5 minutes
- **Model**: Tiny (39MB) for fast processing
- **Storage**: Files deleted after 24 hours
- **Rate limit**: 10 uploads per day per IP

## Monitoring

### View logs:
```bash
docker-compose logs -f
```

### Check resource usage:
```bash
docker stats
```

### Database queries:
```bash
sqlite3 demo.db "SELECT COUNT(*) FROM jobs WHERE date(created_at) = date('now');"
```

## Troubleshooting

### Out of memory:
- Restart container: `docker-compose restart`
- Check model size in environment
- Reduce concurrent processing

### Slow processing:
- Ensure using tiny model for demo
- Check CPU usage: `top`
- Consider upgrading VPS

### Database locked:
- Stop container: `docker-compose down`
- Remove lock: `rm demo.db-journal`
- Restart: `docker-compose up -d`

## Scaling

When ready to scale beyond demo:

1. **Enable authentication** - Add proper user management
2. **Upgrade storage** - Switch to S3 for files
3. **Add queue system** - Handle concurrent requests
4. **Deploy full version** - Use production architecture

## Support

- Documentation: See main project README
- Issues: GitHub Issues
- Email: support@whisper-mowd.com