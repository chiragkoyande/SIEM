.PHONY: help build run dev prod clean logs health

# Default target
help:
	@echo "SentinelWatch SIEM Deployment Commands:"
	@echo "  make build    - Build Docker image"
	@echo "  make dev      - Run development environment"
	@echo "  make prod     - Run production with nginx"
	@echo "  make clean    - Clean up containers and images"
	@echo "  make logs     - View application logs"
	@echo "  make health   - Check application health"
	@echo "  make stop     - Stop all containers"

# Build Docker image
build:
	docker-compose build

# Development deployment
dev:
	docker-compose up --build

# Production deployment
prod:
	docker-compose --profile production up --build -d

# Clean up
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# View logs
logs:
	docker-compose logs -f

# Health check
health:
	@curl -f http://localhost:8000/health || echo "Development health check failed"
	@curl -f http://localhost/health || echo "Production health check failed"

# Stop containers
stop:
	docker-compose down
