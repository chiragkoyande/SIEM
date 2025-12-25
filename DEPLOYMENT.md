# SentinelWatch SIEM Deployment Guide

## Quick Start (Docker)

### 1. Development Deployment
```bash
# Build and run the application
docker-compose up --build

# Access the application
# Dashboard: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### 2. Production Deployment with Nginx
```bash
# Run with nginx reverse proxy
docker-compose --profile production up --build

# Access via nginx
# Dashboard: http://localhost
# API: http://localhost/api/
```

## Manual Deployment

### Prerequisites
- Python 3.10+
- SQLite3
- (Optional) Nginx for reverse proxy

### Steps

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Run the Application**
```bash
# Development
python main.py

# Production with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Environment Variables

Key variables to configure in `.env`:

- `DEBUG=false` - Disable debug mode in production
- `CORS_ORIGINS` - Set allowed origins for security
- `SECRET_KEY` - Generate a secure secret key
- `DATABASE_URL` - Database connection string

## Production Considerations

### Security
- Restrict CORS origins to specific domains
- Use HTTPS with SSL certificates
- Set up firewall rules
- Use environment variables for secrets

### Performance
- Use nginx reverse proxy (provided)
- Enable gzip compression
- Consider PostgreSQL for production database
- Set up proper logging rotation

### Monitoring
- Health check endpoint: `/health`
- Monitor logs in `logs/` directory
- Set up alerting for critical errors

## Docker Volumes

The following directories are persisted:
- `./logs` - Application logs
- `./sentinelwatch.db` - SQLite database

## SSL Setup (Optional)

1. Place SSL certificates in `./ssl/` directory:
   - `cert.pem` - SSL certificate
   - `key.pem` - Private key

2. Uncomment HTTPS section in `nginx.conf`

3. Update `CORS_ORIGINS` to use `https://`

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change port in docker-compose.yml
2. **Database permissions**: Ensure write access to .db file
3. **CORS errors**: Update CORS_ORIGINS environment variable
4. **Memory issues**: Increase Docker memory limits

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# Check Docker container status
docker-compose ps
```

## Scaling

For high-availability deployments:
- Use PostgreSQL instead of SQLite
- Deploy behind a load balancer
- Set up multiple instances with docker-compose scale
- Consider Kubernetes for orchestration
