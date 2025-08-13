# ManageIt - Mess Management System

A comprehensive Flask-based web application for managing mess operations, student feedback, and administrative tasks in educational institutions.

## Features

### 🏠 **Multi-Role Dashboard**
- **Students**: Submit feedback, view menus, track payment history
- **Mess Staff**: Manage menus, view analytics, handle payments
- **Administrators**: System-wide control, notifications, reports

### 🍽️ **Menu Management**
- Dynamic vegetarian and non-vegetarian menu handling
- Temporary menu overrides
- Weekly rotation support (odd/even weeks)
- Real-time menu updates

### 📊 **Feedback System**
- Star-based rating system (1-5 stars)
- Comment collection and analysis
- AI-powered feedback classification
- Critical feedback alerts
- Real-time analytics and reporting

### 💰 **Payment Tracking**
- Non-vegetarian item payment processing
- Payment history tracking
- Revenue analytics
- Multiple payment modes support

### 🗑️ **Waste Management**
- Food waste tracking by floor and meal
- Waste vs feedback correlation analysis
- Sustainability reporting
- Leftover amount monitoring

### 🔔 **Notification System**
- Role-based notifications
- System announcements
- Real-time updates
- Mess switch activity tracking

### 🔒 **Security Features**
- Content Security Policy (CSP) protection
- Rate limiting on sensitive endpoints
- Session management with security headers
- Input validation and sanitization
- IP blocking for suspicious activity
- CSRF protection

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: MySQL with connection pooling
- **Frontend**: HTML5, CSS3, JavaScript, Tailwind CSS
- **Icons**: Phosphor Icons
- **Security**: Flask-Talisman, Flask-Limiter, Flask-WTF
- **AI Integration**: Groq API for feedback analysis
- **Caching**: In-memory caching system
- **Email**: SMTP integration for notifications

## Installation

### Prerequisites
- Python 3.8+
- MySQL 5.7+
- pip (Python package manager)

### Setup Instructions

1. **Clone the repository**
   \`\`\`bash
   git clone <repository-url>
   cd manageit
   \`\`\`

2. **Create virtual environment**
   \`\`\`bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   \`\`\`

3. **Install dependencies**
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

4. **Environment Configuration**
   Create a \`.env\` file in the root directory:
   \`\`\`env
   # Database Configuration
   DB_HOST=localhost
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_NAME=mess_management
   DB_PORT=3306
   
   # Security
   SECRET_KEY=your-super-secret-key-here
   
   # Email Configuration
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   MAIL_DEFAULT_SENDER=your-email@gmail.com
   
   # AI Integration (Optional)
   GROQ_API_KEY=your-groq-api-key
   GROQ_MODEL=llama-3.3-70b-versatile
   
   # Environment
   FLASK_ENV=development
   \`\`\`

5. **Database Setup**
   - Create MySQL database named \`mess_management\`
   - Import the provided SQL schema
   - Ensure proper user permissions

6. **Run the application**
   \`\`\`bash
   python run.py
   \`\`\`

7. **Access the application**
   Open your browser and navigate to \`http://localhost:5000\`

## Project Structure

\`\`\`
manageit/
├── app/
│   ├── blueprints/          # Route handlers
│   │   ├── admin.py         # Admin routes
│   │   ├── auth.py          # Authentication routes
│   │   ├── main.py          # Main routes
│   │   ├── mess.py          # Mess management routes
│   │   └── student.py       # Student routes
│   ├── models/              # Data models
│   │   ├── database.py      # Database connection and queries
│   │   └── feedback_classifier.py  # AI feedback classification
│   ├── services/            # Business logic
│   │   ├── email_service.py
│   │   ├── feedback_service.py
│   │   ├── menu_service.py
│   │   ├── notification_service.py
│   │   ├── payment_service.py
│   │   ├── rating_service.py
│   │   └── waste_service.py
│   ├── static/              # Static files (CSS, JS, images)
│   ├── templates/           # HTML templates
│   └── utils/               # Utility functions
│       ├── cache.py         # Caching system
│       ├── security.py      # Security utilities
│       ├── time_utils.py    # Time handling
│       └── validators.py    # Input validation
├── config/                  # Configuration files
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── README.md               # This file
\`\`\`

## Configuration

### Security Headers
The application implements comprehensive security headers:
- **Content Security Policy (CSP)**: Prevents XSS attacks
- **Strict Transport Security**: Enforces HTTPS
- **X-Frame-Options**: Prevents clickjacking
- **Permissions Policy**: Controls browser features

### Rate Limiting
- Authentication endpoints: 5 requests per minute
- General endpoints: 200 requests per day, 50 per hour
- Health check: 10 requests per minute

### Caching
- Menu data: 1 hour TTL
- Feedback data: 24 hours TTL
- Rating data: 30 minutes TTL
- Notification data: 15 minutes TTL

## API Endpoints

### Authentication
- \`POST /auth/login\` - User login
- \`POST /auth/signup\` - User registration
- \`GET /auth/logout\` - User logout
- \`GET /auth/profile\` - User profile

### Student Routes
- \`GET /student/dashboard\` - Student dashboard
- \`GET /student/feedback\` - Feedback form
- \`POST /student/feedback\` - Submit feedback
- \`GET /student/payment-history\` - Payment history

### Mess Management
- \`GET /mess/dashboard\` - Mess dashboard
- \`GET /mess/add-non-veg-menu\` - Add non-veg items
- \`GET /mess/payment-summary\` - Payment reports
- \`GET /mess/waste-feedback\` - Waste analytics

### Admin Routes
- \`GET /admin/dashboard\` - Admin dashboard
- \`POST /admin/toggle-mess-switch\` - Toggle mess switching
- \`GET /admin/feedback-summary\` - System-wide feedback
- \`GET /admin/send-notification\` - Send notifications

## Database Schema

### Key Tables
- \`users\` - User authentication and profiles
- \`menu\` - Regular menu items
- \`temporary_menu\` - Temporary menu overrides
- \`non_veg_menu_main\` - Non-vegetarian menu management
- \`feedback_summary\` - Feedback submissions
- \`feedback_details\` - Detailed ratings and comments
- \`payment\` - Payment transactions
- \`waste_summary\` - Waste tracking data
- \`notifications\` - System notifications

## Development

### Running in Development Mode
\`\`\`bash
export FLASK_ENV=development
python run.py
\`\`\`

### Code Style
- Follow PEP 8 guidelines
- Use type hints where applicable
- Maintain comprehensive docstrings
- Implement proper error handling

### Testing
\`\`\`bash
# Set test environment
export FLASK_ENV=testing

# Run tests (implement as needed)
python -m pytest tests/
\`\`\`

## Deployment

### Production Considerations
1. **Environment Variables**: Set \`FLASK_ENV=production\`
2. **Database**: Use production MySQL instance
3. **Security**: Enable HTTPS and update security headers
4. **Monitoring**: Implement logging and monitoring
5. **Backup**: Regular database backups

### Docker Deployment (Optional)
\`\`\`dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "run.py"]
\`\`\`

## Monitoring and Maintenance

### Health Check
- Endpoint: \`GET /health\`
- Returns database connectivity status
- Use for load balancer health checks

### Security Monitoring
- Endpoint: \`GET /security/status\` (Admin only)
- Monitor blocked IPs and failed attempts
- Review security logs regularly

### Performance Optimization
- Database query optimization
- Caching strategy implementation
- Static file compression
- CDN integration for static assets

## Contributing

1. Fork the repository
2. Create a feature branch (\`git checkout -b feature/amazing-feature\`)
3. Commit your changes (\`git commit -m 'Add amazing feature'\`)
4. Push to the branch (\`git push origin feature/amazing-feature\`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation for common solutions

## Changelog

### Version 1.0.0
- Initial release with core functionality
- Multi-role dashboard system
- Feedback and rating system
- Payment tracking
- Waste management
- Security implementation

---

**ManageIt** - Streamlining mess management for educational institutions.
\`\`\`
