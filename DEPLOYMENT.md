# Deployment Guide

This guide covers deploying MediGuard AI to various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Local Development](#local-development)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Cloud Deployment](#cloud-deployment)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ minimum, 16GB+ recommended
- **Storage**: 10GB+ for vector stores
- **Network**: Stable internet connection for LLM APIs

### Software Requirements

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Git

## Environment Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

### Required Environment Variables

```bash
# API Configuration
API__HOST=127.0.0.1
API__PORT=8000
API__WORKERS=4

# LLM Configuration (choose one)
GROQ_API_KEY=your_groq_api_key
# OR
OLLAMA_BASE_URL=http://localhost:11434

# Database Configuration
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=StrongPassword123!

# Cache Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Security
SECRET_KEY=your_secret_key_here
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:7860

# Optional: Monitoring
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_SECRET_KEY=your_langfuse_secret
LANGFUSE_PUBLIC_KEY=your_langfuse_public
```

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/Agentic-RagBot.git
cd Agentic-RagBot

# Setup environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\\Scripts\\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize embeddings
python scripts/setup_embeddings.py

# Start development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Using Docker Compose

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api

# Stop services
docker compose down -v
```

## Docker Deployment

### Single Container

```bash
# Build image
docker build -t mediguard-ai .

# Run container
docker run -d \
  --name mediguard \
  -p 8000:8000 \
  -p 7860:7860 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  mediguard-ai
```

### Production with Docker Compose

```bash
# Use production compose file
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale API services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale api=3
```

### Production Docker Compose Override

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    environment:
      - API__WORKERS=8
      - API__RELOAD=false
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api

  opensearch:
    environment:
      - cluster.name=mediguard-prod
      - "OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g"
    deploy:
      resources:
        limits:
          memory: 4G
```

## Kubernetes Deployment

### Namespace and ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mediguard

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mediguard-config
  namespace: mediguard
data:
  API__HOST: "0.0.0.0"
  API__PORT: "8000"
  OPENSEARCH__HOST: "opensearch"
  OPENSEARCH__PORT: "9200"
  REDIS__HOST: "redis"
  REDIS__PORT: "6379"
```

### Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mediguard-secrets
  namespace: mediguard
type: Opaque
data:
  GROQ_API_KEY: <base64-encoded-key>
  SECRET_KEY: <base64-encoded-secret>
  OPENSEARCH_PASSWORD: <base64-encoded-password>
```

### Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mediguard-api
  namespace: mediguard
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mediguard-api
  template:
    metadata:
      labels:
        app: mediguard-api
    spec:
      containers:
      - name: api
        image: mediguard-ai:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: mediguard-config
        - secretRef:
            name: mediguard-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service and Ingress

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mediguard-service
  namespace: mediguard
spec:
  selector:
    app: mediguard-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mediguard-ingress
  namespace: mediguard
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.mediguard-ai.com
    secretName: mediguard-tls
  rules:
  - host: api.mediguard-ai.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mediguard-service
            port:
              number: 80
```

## Cloud Deployment

### AWS ECS

1. Create ECR repository:
```bash
aws ecr create-repository --repository-name mediguard-ai
```

2. Push image:
```bash
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com
docker tag mediguard-ai:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/mediguard-ai:latest
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/mediguard-ai:latest
```

3. Deploy using ECS task definition

### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT-ID/mediguard-ai

# Deploy
gcloud run deploy mediguard-ai \
  --image gcr.io/PROJECT-ID/mediguard-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --max-instances 10
```

### Azure Container Instances

```bash
# Create resource group
az group create --name mediguard-rg --location eastus

# Deploy container
az container create \
  --resource-group mediguard-rg \
  --name mediguard-ai \
  --image mediguard-ai:latest \
  --cpu 1 \
  --memory 2 \
  --ports 8000 \
  --environment-variables \
    API__HOST=0.0.0.0 \
    API__PORT=8000
```

## Monitoring and Logging

### Prometheus Metrics

Add to your FastAPI app:

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

### ELK Stack

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch-data:
```

### Health Checks

The application includes built-in health checks:

```bash
# Basic health
curl http://localhost:8000/health

# Detailed health with dependencies
curl http://localhost:8000/health/detailed
```

## Security Considerations

### SSL/TLS Configuration

```nginx
# nginx/nginx.conf
server {
    listen 443 ssl http2;
    server_name api.mediguard-ai.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Rate Limiting

```python
# Add to main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/analyze")
@limiter.limit("10/minute")
async def analyze():
    pass
```

### Security Headers

```python
# Already included in src/middlewares.py
SecurityHeadersMiddleware adds:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security
```

## Troubleshooting

### Common Issues

1. **Memory Issues**:
   - Increase container memory limits
   - Optimize vector store size
   - Use Redis for caching

2. **Slow Response Times**:
   - Check LLM provider latency
   - Optimize retriever settings
   - Add caching layers

3. **Database Connection Errors**:
   - Verify OpenSearch is running
   - Check network connectivity
   - Validate credentials

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python -m src.main
```

### Performance Tuning

1. **Vector Store Optimization**:
   ```python
   # Adjust in config
   RETRIEVAL_K=10  # Reduce for faster retrieval
   EMBEDDING_BATCH_SIZE=32  # Optimize based on GPU memory
   ```

2. **Async Optimization**:
   ```python
   # Use connection pooling
   HTTPX_LIMITS=httpx.Limits(max_connections=100, max_keepalive_connections=20)
   ```

3. **Caching Strategy**:
   ```python
   # Cache frequent queries
   CACHE_TTL=3600  # 1 hour
   CACHE_MAX_SIZE=1000
   ```

## Backup and Recovery

### Data Backup

```bash
# Backup vector stores
docker exec opensearch tar czf /backup/$(date +%Y%m%d)_opensearch.tar.gz /usr/share/opensearch/data

# Backup Redis
docker exec redis redis-cli BGSAVE
docker cp redis:/data/dump.rdb ./backup/redis_$(date +%Y%m%d).rdb
```

### Disaster Recovery

1. Restore from backups
2. Verify data integrity
3. Update configuration if needed
4. Restart services

## Scaling Guidelines

### Horizontal Scaling

- Use load balancer (nginx/HAProxy)
- Deploy multiple API instances
- Consider session affinity if needed

### Vertical Scaling

- Monitor resource usage
- Adjust CPU/memory limits
- Optimize database queries

### Auto-scaling (Kubernetes)

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mediguard-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mediguard-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Support

For deployment issues:
- Check logs: `docker compose logs -f`
- Review monitoring dashboards
- Consult troubleshooting guide
- Contact support at deploy@mediguard-ai.com
