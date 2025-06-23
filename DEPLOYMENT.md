# 🚀 Deployment Guide

## GitHub Secrets Configuration

Before pushing to GitHub and enabling CI/CD, configure these secrets in your repository:

### Required GitHub Secrets

Go to: `Settings → Secrets and variables → Actions → Repository secrets`

Add the following secrets:

```
JWT_SECRET=your-jwt-secret-here
MONGODB_URL=your-mongodb-connection-string
MONGODB_DATABASE=your-database-name
PERPLEXITY_API_KEY=your-perplexity-api-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
ZEPTO_API_KEY=your-zepto-api-key
WEBHOOK_API_KEY=your-webhook-api-key
SSH_PRIVATE_KEY=your-ssh-private-key-content
SERVER_HOST=your-server-ip-address
SERVER_USER=ubuntu
```

### Local Development Setup

1. Copy the example environment file:
   ```bash
   cp Backend/Backend.env.example Backend/Backend.env
   ```

2. Fill in your local development values in `Backend/Backend.env`

3. Never commit the actual `Backend.env` file (it's in .gitignore)

## Deployment Process

### Automatic Deployment
- Push to `main` branch triggers automatic deployment
- GitHub Actions will create the environment file from secrets
- Backend will be deployed and restarted automatically

### Manual Deployment
```bash
# Trigger manual deployment
gh workflow run deploy-backend.yml
```

### Local Testing
```bash
cd Backend
python -m uvicorn main:app --reload
```

## Security Best Practices

✅ **All secrets stored in GitHub Secrets**
✅ **No hardcoded credentials in code**
✅ **Environment file excluded from git**
✅ **Separate dev/prod configurations**
✅ **Automated deployment with health checks**

## Troubleshooting

### Backend not starting
1. Check GitHub Actions logs
2. SSH to server and check backend.log
3. Verify all required secrets are set

### Environment issues
1. Ensure Backend.env exists on server
2. Check file permissions (should be readable by ubuntu user)
3. Verify all required environment variables are present