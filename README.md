# ManageIt - Comprehensive Mess Management System

A robust, secure, and feature-rich mess management system built with Flask, designed to streamline operations for educational institutions and corporate cafeterias.

## 🌟 Features

### Multi-Role Dashboard System
- **Students**: View menus, make payments, provide feedback, track meal history
- **Mess Staff**: Manage menus, track waste, view feedback, handle payments
- **Administrators**: Complete system oversight, analytics, user management

### Core Functionality
- **Menu Management**: Dynamic daily menu creation with vegetarian/non-vegetarian options
- **Payment Processing**: Multiple payment methods with transaction tracking
- **Feedback System**: AI-powered sentiment analysis and rating system
- **Waste Tracking**: Environmental monitoring with waste reduction insights
- **Real-time Notifications**: System-wide announcements and alerts
- **Advanced Analytics**: Comprehensive reporting and data visualization

### Security Features
- **Multi-layer Authentication**: Secure login with session management
- **Rate Limiting**: Protection against brute force attacks
- **Content Security Policy**: XSS and injection attack prevention
- **Input Validation**: Comprehensive data sanitization
- **Security Logging**: Detailed audit trails and monitoring
- **HTTPS Enforcement**: SSL/TLS encryption for all communications

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- MySQL 8.0+
- Redis 6.0+
- Docker & Docker Compose (recommended)

### Installation

#### Option 1: Docker Deployment (Recommended)
\`\`\`bash
# Clone the repository
git clone https://github.com/yourusername/manageit.git
cd manageit

# Copy and configure environment variables
cp .env.production .env
# Edit .env with your actual values

# Deploy with Docker
chmod +x deploy.sh
./deploy.sh
\`\`\`

#### Option 2: Manual Installation
\`\`\`bash
# Clone and setup
git clone https://github.com/yourusername/manageit.git
cd manageit

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
mysql -u root -p < init.sql

# Configure environment
cp .env.production .env
# Edit .env with your values

# Run application
export FLASK_ENV=production
gunicorn -w 4 -b 0.0.0.0:8000 'run:create_app("production")'
\`\`\`

## 🏗️ Architecture

### Technology Stack
- **Backend**: Flask 2.3.3 with Gunicorn WSGI server
- **Database**: MySQL 8.0 with connection pooling
- **Caching**: Redis for session storage and rate limiting
- **Frontend**: HTML5, CSS3, JavaScript with responsive design
- **Security**: Flask-Talisman, Flask-WTF, Flask-Limiter
- **Deployment**: Docker, Nginx reverse proxy, SSL/TLS

### Project Structure
\`\`\`
manageit/
├── app/
│   ├── blueprints/          # Route handlers
│   │   ├── auth.py         # Authentication routes
│   │   ├── student.py      # Student dashboard
│   │   ├── mess.py         # Mess management
│   │   └── admin.py        # Admin panel
│   ├── models/             # Database models
│   ├── templates/          # Jinja2 templates
│   ├── static/            # CSS, JS, images
│   └── utils/             # Utility functions
├── config.py              # Configuration management
├── run.py                # Application factory
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── docker-compose.prod.yml # Production deployment
├── nginx.conf          # Reverse proxy config
└── init.sql           # Database schema
\`\`\`

## ⚙️ Configuration

### Environment Variables
\`\`\`bash
# Security
SECRET_KEY=your-super-strong-secret-key-here

# Database
DB_HOST=your-db-host
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_NAME=mess_management_prod

# Redis
REDIS_URL=redis://your-redis-host:6379/0

# Email
MAIL_SERVER=smtp.your-domain.com
MAIL_USERNAME=noreply@your-domain.com
MAIL_PASSWORD=your-email-password

# AI Integration (Optional)
GROQ_API_KEY=your-groq-api-key
\`\`\`

### Security Configuration
- **Rate Limiting**: 100 requests/day, 20/hour for production
- **Session Security**: HTTPOnly, Secure, SameSite cookies
- **CSRF Protection**: Enabled with 1-hour token lifetime
- **Content Security Policy**: Strict policy with external resource allowlist
- **HTTPS**: Enforced in production with HSTS headers

## 📊 API Endpoints

### Authentication
- `POST /auth/login` - User authentication
- `POST /auth/signup` - User registration
- `GET /auth/logout` - Session termination
- `GET /auth/profile` - User profile management

### Student Dashboard
- `GET /student/dashboard` - Main dashboard
- `GET /student/menu` - Daily menu view
- `POST /student/feedback` - Submit feedback
- `GET /student/payments` - Payment history

### Mess Management
- `GET /mess/dashboard` - Mess staff dashboard
- `POST /mess/menu` - Menu management
- `GET /mess/feedback` - View feedback
- `POST /mess/waste` - Waste tracking

### Administration
- `GET /admin/dashboard` - Admin overview
- `GET /admin/analytics` - System analytics
- `POST /admin/notifications` - Send notifications
- `GET /admin/users` - User management

### System
- `GET /health` - Application health check
- `GET /security/status` - Security monitoring (admin only)

## 🗄️ Database Schema

### Core Tables
- **users**: User accounts and authentication
- **mess_halls**: Mess facility information
- **menu_items**: Daily menu management
- **payments**: Transaction records
- **feedback**: User feedback and ratings
- **waste_tracking**: Environmental monitoring
- **notifications**: System announcements
- **security_logs**: Audit trail

### Key Features
- **Referential Integrity**: Foreign key constraints
- **Performance Optimization**: Strategic indexing
- **Data Validation**: Check constraints and triggers
- **Audit Trail**: Comprehensive logging system

## 🔧 Development

### Local Development Setup
\`\`\`bash
# Clone repository
git clone https://github.com/yourusername/manageit.git
cd manageit

# Setup development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure development environment
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key

# Run development server
python run.py
\`\`\`

### Testing
\`\`\`bash
# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=app tests/

# Security testing
bandit -r app/
\`\`\`

### Code Quality
\`\`\`bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
pylint app/
\`\`\`

## 🚀 Production Deployment

### Prerequisites
- Ubuntu 20.04+ or CentOS 8+
- Docker & Docker Compose
- SSL certificates (Let's Encrypt recommended)
- Domain name with DNS configuration

### Deployment Steps
1. **Server Setup**
   \`\`\`bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   \`\`\`

2. **Application Deployment**
   \`\`\`bash
   # Clone and configure
   git clone https://github.com/yourusername/manageit.git
   cd manageit
   cp .env.production .env
   # Edit .env with production values
   
   # Deploy
   chmod +x deploy.sh
   ./deploy.sh
   \`\`\`

3. **SSL Configuration**
   \`\`\`bash
   # Get SSL certificates
   sudo certbot --nginx -d your-domain.com
   \`\`\`

4. **Monitoring Setup**
   \`\`\`bash
   # Setup monitoring
   ./monitor.sh
   
   # View logs
   docker-compose -f docker-compose.prod.yml logs -f
   \`\`\`

### Performance Optimization
- **Database**: Connection pooling, query optimization
- **Caching**: Redis for session storage and rate limiting
- **Static Files**: Nginx serving with compression
- **Load Balancing**: Multiple Gunicorn workers

## 📈 Monitoring & Maintenance

### Health Monitoring
- **Application Health**: `/health` endpoint
- **Database Health**: Connection and query monitoring
- **Security Monitoring**: Failed login attempts, blocked IPs
- **Performance Metrics**: Response times, error rates

### Backup Strategy
\`\`\`bash
# Automated database backups
chmod +x backup.sh
./backup.sh

# Schedule regular backups
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
\`\`\`

### Log Management
- **Application Logs**: `/var/log/manageit/app.log`
- **Security Logs**: Database security_logs table
- **Access Logs**: Nginx access logs
- **Error Logs**: Application and system error logs

### Maintenance Tasks
- **Database Optimization**: Regular ANALYZE and OPTIMIZE
- **Log Rotation**: Automated with logrotate
- **Security Updates**: Regular system and dependency updates
- **Certificate Renewal**: Automated with certbot

## 🔒 Security

### Security Features
- **Authentication**: Multi-factor authentication support
- **Authorization**: Role-based access control
- **Data Protection**: Encryption at rest and in transit
- **Input Validation**: Comprehensive sanitization
- **Rate Limiting**: DDoS and brute force protection
- **Security Headers**: HSTS, CSP, X-Frame-Options
- **Audit Logging**: Comprehensive security event logging

### Security Best Practices
- Regular security audits and penetration testing
- Dependency vulnerability scanning
- Security header validation
- SSL/TLS configuration testing
- Database security hardening

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards
- Follow PEP 8 style guidelines
- Write comprehensive tests
- Document all functions and classes
- Use type hints where appropriate
- Maintain security best practices

### Issue Reporting
- Use GitHub Issues for bug reports
- Include detailed reproduction steps
- Provide system information and logs
- Follow the issue template

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Security Guide](docs/security.md)
- [Troubleshooting](docs/troubleshooting.md)

### Community
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community support and questions
- **Wiki**: Additional documentation and guides

### Professional Support
For enterprise support, custom development, or consulting services, contact: support@manageit.com

## 🙏 Acknowledgments

- Flask community for the excellent web framework
- Security researchers for vulnerability disclosures
- Contributors and beta testers
- Open source libraries and tools used in this project

---

**ManageIt** - Streamlining mess management with security, efficiency, and user experience at its core.
