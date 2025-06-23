# MyDSCVR DataCollection Pipeline

🤖 **AI-Powered Event Data Collection & Processing System**

## Overview

Automated data collection pipeline that discovers, extracts, enhances, and categorizes Dubai events using AI-powered systems. Runs scheduled collections via cron jobs and feeds data to the MyDSCVR backend API.

## Features

- 🔍 **Automated Event Discovery** - Perplexity AI-powered event searching
- 🎯 **Smart Categorization** - AI-enhanced event classification  
- 👨‍👩‍👧‍👦 **Family Suitability Analysis** - Intelligent family-friendly scoring
- 🔄 **Real-time Processing** - Continuous data collection and enhancement
- 📊 **Quality Control** - Data validation and deduplication
- ⏰ **Scheduled Collections** - Automated cron-based data gathering

## Tech Stack

- **Language**: Python 3.12
- **AI**: Perplexity API for content generation
- **Database**: MongoDB Atlas
- **Processing**: AsyncIO for concurrent operations
- **Deployment**: GitHub Actions + AWS EC2
- **Scheduling**: Cron jobs for automated collection

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Perplexity    │────│  DataCollection │────│   MongoDB Atlas │
│      API        │    │    Pipeline     │    │    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │   MyDSCVR API   │
                       │    Backend      │
                       └─────────────────┘
```

## Collection Schedule

- **1:00 AM UTC** - Primary event collection (88 queries)
- **1:15 AM UTC** - Hidden gems generation
- **3:00 AM UTC** - Data deduplication
- **3:15 PM UTC** - Afternoon refresh collection

## Key Components

### Event Extraction (`perplexity_events_extractor.py`)
- AI-powered event discovery using Perplexity API
- Handles 88+ search queries across all categories
- Extracts structured event data with family scoring

### Data Storage (`perplexity_storage.py`) 
- MongoDB integration with deduplication
- Event validation and quality control
- Session tracking and analytics

### Configuration (`config/perplexity_settings.py`)
- Environment-based configuration management
- Rate limiting and timeout controls
- Category mapping and search optimization

## Environment Configuration

All secrets managed via GitHub Secrets and consolidated in `DataCollection.env`:

- MongoDB connection details
- Perplexity API credentials  
- Backend integration settings
- Rate limiting configuration

## Deployment

Automated deployment via GitHub Actions:
- Push to `main` triggers deployment
- Environment file created from GitHub secrets
- Dependencies updated automatically
- Configuration tested post-deployment

## Live System

🔗 **Production Data Collection**: Runs on AWS EC2  
📊 **MongoDB Database**: Atlas cluster with 97+ events  
🎭 **Hidden Gems**: Daily AI-generated recommendations  

---

**Part of the MyDSCVR ecosystem - Powering Dubai's event discovery platform** 🌟