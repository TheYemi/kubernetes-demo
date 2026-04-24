# for local dev actually

if you want to run the application locally with Docker Compose:

```bash
docker compose -f docker-compose.dev.yaml up --build
```

Visit http://localhost:5000

**Note:** it's is for local testing only, production deployment uses my kubernetes manifests in `kubernetes/`.
