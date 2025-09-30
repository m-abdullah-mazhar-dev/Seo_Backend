# SEO Automation Backend

A comprehensive Django-based SEO automation platform that provides AI-powered content generation, keyword optimization, Google My Business management, and WordPress integration for businesses.

## 🚀 Features

### Core SEO Services
- **AI-Powered Blog Writing**: Automated blog content generation using advanced AI models
- **Keyword Optimization**: DataForSEO integration for keyword research and optimization
- **SEO Content Optimization**: Automated on-page SEO improvements
- **Google My Business Posts**: Automated GMB post creation and management
- **WordPress Integration**: Seamless content publishing to WordPress sites

### Analytics & Monitoring
- **Google Analytics Integration**: Real-time analytics data collection
- **Google Search Console**: Search performance monitoring
- **Keyword Ranking Tracking**: Automated ranking position monitoring
- **Performance Metrics**: Click-through rates, impressions, and position tracking

### Business Management
- **Multi-Service Support**: Handle multiple business services
- **Service Area Management**: Geographic service area optimization
- **Business Location Tracking**: Multiple location management
- **CRM Integration**: HubSpot, Zoho, Jobber, Zendesk, and Salesforce support

### Subscription & Payment
- **Stripe Integration**: Secure payment processing
- **Package Management**: Flexible subscription tiers
- **Usage Tracking**: Monthly limit monitoring
- **Automated Billing**: Recurring subscription management

## 🛠️ Technology Stack

### Backend
- **Django 5.2**: Web framework
- **Django REST Framework**: API development
- **Celery**: Asynchronous task processing
- **Redis**: Message broker and caching
- **SQLite**: Database (development)
- **PostgreSQL**: Database (production ready)

### AI & Data Services
- **OpenAI GPT**: Content generation
- **DataForSEO API**: Keyword research and SEO data
- **Google APIs**: Analytics, Search Console, My Business
- **BeautifulSoup**: Web scraping
- **Selenium**: Browser automation

### Authentication & Security
- **JWT Authentication**: Secure API access
- **Django AllAuth**: Social authentication (Google)
- **CORS Support**: Cross-origin resource sharing
- **Environment Variables**: Secure configuration management

## 📁 Project Structure

```
SEO_Automation/
├── authentication/          # User management and authentication
├── seo_services/           # Core SEO automation features
├── g_matrix/              # Google Analytics and Search Console
├── job/                   # Job management and CRM integration
├── payment/               # Stripe payment processing
├── SEO_Automation/        # Django project settings
└── requirements.txt       # Python dependencies
```

### Key Apps

#### `seo_services/`
- **Models**: ServiceArea, Keyword, SEOTask, Blog, ServicePage
- **Features**: Blog writing, keyword optimization, SEO tasks
- **APIs**: WordPress integration, content generation

#### `g_matrix/`
- **Models**: GoogleAnalyticsToken, GoogleBusinessToken
- **Features**: Analytics data collection, GMB management
- **APIs**: Google API integrations

#### `job/`
- **Models**: JobTask, CRM integrations
- **Features**: Job management, CRM synchronization
- **APIs**: Multi-CRM support

#### `authentication/`
- **Models**: Custom User model
- **Features**: JWT authentication, social login
- **APIs**: User registration, login, profile management

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Redis server
- Virtual environment

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SEO_Automation
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Start services**
   ```bash
   # Terminal 1: Django server
   python manage.py runserver
   
   # Terminal 2: Celery worker
   celery -A SEO_Automation worker --loglevel=info
   
   # Terminal 3: Celery beat (scheduler)
   celery -A SEO_Automation beat --loglevel=info
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=sqlite:///db.sqlite3

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis
REDIS_URL=redis://localhost:6379/0

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Google APIs
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# DataForSEO
DATAFORSEO_EMAIL=your-email
DATAFORSEO_KEY=your-api-key

# AI API
AI_API_DOMAIN=http://your-ai-service:5000

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password
```

### Google API Setup

1. **Google Search Console**
   - Enable Google Search Console API
   - Create OAuth 2.0 credentials
   - Configure redirect URIs

2. **Google Analytics**
   - Enable Google Analytics Reporting API
   - Set up service account or OAuth

3. **Google My Business**
   - Enable Google My Business API
   - Configure OAuth credentials

## 📊 API Endpoints

### Authentication
- `POST /auth/register/` - User registration
- `POST /auth/login/` - User login
- `POST /auth/logout/` - User logout
- `POST /auth/refresh/` - Token refresh

### SEO Services
- `GET /seo/services/` - List user services
- `POST /seo/services/` - Create new service
- `GET /seo/keywords/` - List keywords
- `POST /seo/keywords/` - Add keywords
- `GET /seo/tasks/` - List SEO tasks
- `POST /seo/tasks/` - Create SEO task

### WordPress Integration
- `POST /seo/wordpress/connect/` - Connect WordPress
- `GET /seo/wordpress/verify/` - Verify connection
- `POST /seo/service-pages/` - Submit service page

### Analytics
- `GET /analytics/overview/` - Analytics overview
- `GET /analytics/keywords/` - Keyword performance
- `POST /analytics/sync/` - Sync analytics data

## 🔄 Automated Tasks

### SEO Tasks
- **Blog Writing**: AI-generated blog posts
- **Keyword Optimization**: DataForSEO keyword research
- **SEO Optimization**: On-page SEO improvements
- **GMB Posts**: Google My Business content

### Scheduling
- **Celery Beat**: Automated task scheduling
- **Monthly Limits**: Package-based usage tracking
- **Priority Queuing**: Task prioritization system

## 🏗️ Database Schema

### Key Models

#### User Management
- `User`: Custom user model with subscription support
- `OnboardingForm`: Business onboarding data
- `Package`: Subscription packages

#### SEO Services
- `Service`: Business services
- `Keyword`: SEO keywords with metrics
- `SEOTask`: Automated SEO tasks
- `Blog`: Generated blog content
- `ServiceArea`: Geographic service areas

#### Analytics
- `GoogleAnalyticsToken`: GA authentication
- `AnalyticsSummary`: Performance data
- `KeywordData`: Keyword metrics

## 🔒 Security Features

- **JWT Authentication**: Secure API access
- **CORS Configuration**: Cross-origin security
- **Environment Variables**: Sensitive data protection
- **Input Validation**: Data sanitization
- **Rate Limiting**: API usage limits

## 📈 Monitoring & Logging

- **Structured Logging**: Comprehensive logging system
- **Error Tracking**: Exception monitoring
- **Performance Metrics**: Task execution tracking
- **Usage Analytics**: User activity monitoring

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure production database
- [ ] Set up Redis server
- [ ] Configure email settings
- [ ] Set up SSL certificates
- [ ] Configure domain settings
- [ ] Set up monitoring

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## 🔄 Changelog

### Version 1.0.0
- Initial release
- Core SEO automation features
- WordPress integration
- Google Analytics support
- Stripe payment integration

---

**Built with ❤️ for SEO professionals and businesses**
