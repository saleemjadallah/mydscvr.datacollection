# 🚀 Frontend Deployment Guide

## Overview
This guide covers the complete deployment process for the MyDscvr frontend application, including setup, troubleshooting, and best practices.

## Repository Structure
```
Frontend/
├── .github/workflows/deploy-frontend.yml  # CI/CD pipeline
├── dxb_events_web/                        # Flutter web application
├── Frontend.env                           # Environment variables template
├── web/_redirects                         # Netlify proxy configuration
├── DEPLOYMENT.md                          # This guide
└── README.md                              # Project documentation
```

## 1. Initial Setup

### Required GitHub Secrets
Navigate to: `Settings → Secrets and variables → Actions`

**Authentication & Core:**
```
GOOGLE_CLIENT_ID=your_google_client_id_here
NETLIFY_AUTH_TOKEN=your_netlify_auth_token
NETLIFY_SITE_ID=your_netlify_site_id
GITHUB_TOKEN=automatically_provided
```

**Backend Configuration:**
```
BACKEND_URL=https://mydscvr.xyz
DATA_COLLECTION_URL=https://mydscvr.xyz
FALLBACK_API_URL=https://mydscvr.xyz/api
FALLBACK_DATA_URL=https://mydscvr.xyz/api
```

**Optional Configuration:**
```
ENABLE_LOGS=true
ENABLE_PERFORMANCE_OVERLAY=false
CUSTOM_DOMAIN=mydscvr.ai
CDN_URL=your_cdn_url
SENTRY_DSN=your_sentry_dsn
LOG_LEVEL=info
```

⚠️ **CRITICAL:** Do NOT set `API_BASE_URL` as a GitHub secret. It's hardcoded to `/api` in the workflow to ensure proper Netlify proxy usage.

### Local Development Setup
```bash
# Clone repository
git clone https://github.com/your-username/mydscvr.frontend.git
cd Frontend/dxb_events_web

# Install Flutter dependencies
flutter pub get

# Generate code if needed
flutter packages pub run build_runner build --delete-conflicting-outputs

# Run locally
flutter run -d chrome
```

## 2. Deployment Methods

### Automatic Deployment (Recommended)
```bash
# Any push to main branch triggers automatic deployment
git add .
git commit -m "Your descriptive commit message"
git push origin main

# Monitor progress at:
# https://github.com/your-username/mydscvr.frontend/actions
```

### Manual Deployment
1. Go to **GitHub Actions** tab
2. Select **"Deploy Frontend to Netlify"**
3. Click **"Run workflow"**
4. Choose environment: `production`, `staging`, or `development`
5. Click **"Run workflow"**

### Emergency Deployment
```bash
# For urgent fixes, push directly to main
git add .
git commit -m "HOTFIX: Description of urgent fix"
git push origin main

# Monitor deployment closely
```

## 3. Key Configuration Files

### GitHub Actions Workflow
**File:** `.github/workflows/deploy-frontend.yml`

**Critical Configuration:**
```yaml
# Line 101 - CORS fix (DO NOT CHANGE)
--dart-define=API_BASE_URL="/api" \

# Flutter version
FLUTTER_VERSION: '3.32.4'

# Build settings
--no-tree-shake-icons \
--release \
```

### Netlify Proxy Configuration
**File:** `dxb_events_web/web/_redirects`

```
# API proxy - Routes /api/* to backend
/api/* https://mydscvr.xyz/api/:splat 200

# SPA routing - Fallback to index.html
/* /index.html 200
```

**Why this matters:** The proxy prevents CORS issues by routing frontend API calls through Netlify.

## 4. Common Issues & Solutions

### CORS Errors (Most Common)
**Symptoms:**
- Events not loading
- Console errors: "Access to XMLHttpRequest blocked by CORS policy"
- Network tab shows direct calls to `mydscvr.xyz`

**Solution:**
```yaml
# Ensure this line exists in deploy-frontend.yml:
--dart-define=API_BASE_URL="/api" \

# NOT this:
--dart-define=API_BASE_URL="${{ secrets.API_BASE_URL }}" \
```

### Build Failures
**Flutter Version Mismatch:**
```bash
# Check local Flutter version
flutter --version

# Should match workflow version: 3.32.4
```

**Dependency Issues:**
```bash
cd dxb_events_web
flutter clean
flutter pub get
flutter pub upgrade
```

**Code Generation Errors:**
```bash
flutter packages pub run build_runner clean
flutter packages pub run build_runner build --delete-conflicting-outputs
```

### Compilation Errors
**Missing Imports:**
```dart
// Common fixes needed:
import '../event_details/event_details_screen.dart';  // Not ../events/
```

**Class Name Mismatches:**
```dart
// Use correct class names:
EventDetailsScreen(eventId: event.id, event: event)  // Not EventDetailScreen
```

### Environment Variable Issues
**Check GitHub Secrets:**
1. Go to repository settings
2. Navigate to "Secrets and variables" → "Actions"
3. Verify all required secrets are present
4. Secrets should not have quotes around values

**Debug Environment Variables:**
```yaml
# Add to workflow for debugging:
- name: Debug Environment
  run: |
    echo "Environment: ${{ github.event.inputs.environment || 'production' }}"
    echo "API Base URL will be: /api"
```

## 5. Deployment Monitoring

### GitHub Actions
**URL:** `https://github.com/your-username/mydscvr.frontend/actions`

**What to Watch For:**
- ✅ Build completed successfully
- ✅ All tests passed
- ✅ Deploy to Netlify succeeded
- ✅ Post-deployment verification passed

**Common Failure Points:**
- Flutter analysis warnings
- Test failures
- Netlify deployment timeouts
- Missing environment variables

### Netlify Dashboard
**URL:** `https://app.netlify.com/sites/your-site-id/deploys`

**Key Indicators:**
- ✅ Status: "Published"
- ✅ Branch: "main"
- ✅ Build time: < 10 minutes
- ✅ No error logs

### Production Health Check
After deployment, verify:
- [ ] Site loads: `https://mydscvr.ai`
- [ ] Events are visible on homepage
- [ ] Category pages work
- [ ] Search functionality works
- [ ] No console errors
- [ ] API calls use `/api/` prefix (not direct `mydscvr.xyz`)

## 6. Rollback Procedures

### Netlify Dashboard Rollback
1. Go to Netlify dashboard
2. Click on "Deploys" tab
3. Find previous working deploy
4. Click "Publish deploy"
5. Site immediately rolls back

### Git Rollback
```bash
# Revert last commit
git revert HEAD
git push origin main

# Revert specific commit
git revert <commit-hash>
git push origin main

# Hard reset (use carefully)
git reset --hard <previous-commit-hash>
git push --force origin main
```

## 7. Performance Optimization

### Build Optimization
```yaml
# Current build settings:
flutter build web \
  --release \
  --no-tree-shake-icons \
  --dart-define=ENVIRONMENT=production \
```

### Bundle Size Monitoring
```bash
# Check build output (in workflow logs):
echo "Total build size:"
du -sh dxb_events_web/build/web/
```

### Asset Optimization
- Compress images before adding to assets
- Use WebP format when possible
- Minimize JavaScript bundle size
- Enable gzip compression on Netlify

## 8. Security Best Practices

### Secrets Management
- Never commit secrets to repository
- Use GitHub secrets for sensitive data
- Rotate API keys regularly
- Monitor secret usage in Actions

### Code Security
```bash
# Security scan runs automatically on PRs
# Checks for:
- Hardcoded API keys
- Exposed secrets
- Vulnerable dependencies
```

### Content Security Policy
```
# Configured via CSP_POLICY secret
# Restricts resource loading for security
```

## 9. Development Workflow

### Feature Development
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test locally
flutter run -d chrome

# Push and create PR
git push origin feature/your-feature-name
# Create pull request on GitHub
```

### Code Quality
```bash
# Before committing:
flutter analyze
flutter test
dart format lib/
```

### PR Process
1. Create pull request
2. Security scan runs automatically
3. Code review by team
4. Merge to main triggers deployment

## 10. Troubleshooting Checklist

**Deployment Failed:**
- [ ] Check GitHub Actions logs
- [ ] Verify all secrets are set
- [ ] Ensure Flutter version matches workflow
- [ ] Run `flutter analyze` locally

**Site Not Loading:**
- [ ] Check Netlify deploy status
- [ ] Verify custom domain DNS settings
- [ ] Check for SSL certificate issues
- [ ] Review Netlify build logs

**Events Not Loading:**
- [ ] Check browser network tab
- [ ] Verify API calls use `/api/` prefix
- [ ] Check backend service status
- [ ] Review CORS configuration

**Build Errors:**
- [ ] Update Flutter dependencies
- [ ] Run code generation
- [ ] Check import paths
- [ ] Verify class names match

## 11. Contact & Support

**Development Team:**
- Frontend Issues: Check GitHub Issues
- Backend Issues: Contact backend team
- Infrastructure: Contact DevOps team

**Useful Links:**
- [GitHub Repository](https://github.com/your-username/mydscvr.frontend)
- [Netlify Dashboard](https://app.netlify.com/sites/your-site-id)
- [Production Site](https://mydscvr.ai)
- [Flutter Documentation](https://docs.flutter.dev)

---

## Quick Reference Commands

```bash
# Local development
flutter run -d chrome

# Build for web
flutter build web --release

# Deploy to production
git push origin main

# Emergency rollback
# Use Netlify dashboard or git revert

# Check deployment status
# GitHub Actions → Deploy Frontend to Netlify
```

---

**Last Updated:** $(date +"%Y-%m-%d")
**Version:** 1.0
**Maintained by:** Development Team