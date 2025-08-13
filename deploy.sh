#!/bin/bash

# Production Deployment Script for ManageIt
# Run this script to deploy the application to production

set -e  # Exit on any error

echo "🚀 Starting ManageIt Production Deployment..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root for security reasons"
   exit 1
fi

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production file not found!"
    echo "Please copy .env.production template and fill in your values"
    exit 1
fi

# Load environment variables
source .env.production

# Validate required environment variables
required_vars=("SECRET_KEY" "DB_HOST" "DB_USER" "DB_PASSWORD" "DB_NAME")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Create necessary directories
echo "📁 Creating directories..."
sudo mkdir -p /var/log/manageit
sudo chown $USER:$USER /var/log/manageit
mkdir -p logs
mkdir -p uploads
mkdir -p ssl

echo "✅ Directories created"

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv mysql-client redis-tools nginx certbot python3-certbot-nginx

echo "✅ System dependencies installed"

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Python dependencies installed"

# Database setup
echo "🗄️ Setting up database..."
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD < init.sql
echo "✅ Database initialized"

# Generate SSL certificates (Let's Encrypt)
echo "🔒 Setting up SSL certificates..."
if [ ! -f "ssl/cert.pem" ]; then
    echo "Generating self-signed certificates for testing..."
    echo "For production, use: sudo certbot --nginx -d your-domain.com"
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
fi

echo "✅ SSL certificates ready"

# Build Docker images
echo "🐳 Building Docker images..."
docker-compose -f docker-compose.prod.yml build

echo "✅ Docker images built"

# Start services
echo "🚀 Starting services..."
docker-compose -f docker-compose.prod.yml up -d

echo "⏳ Waiting for services to start..."
sleep 30

# Health check
echo "🏥 Performing health check..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Application is healthy!"
else
    echo "❌ Health check failed!"
    echo "Check logs: docker-compose -f docker-compose.prod.yml logs"
    exit 1
fi

# Setup log rotation
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/manageit > /dev/null <<EOF
/var/log/manageit/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker-compose -f $(pwd)/docker-compose.prod.yml restart app
    endscript
}
EOF

echo "✅ Log rotation configured"

# Setup monitoring script
echo "📊 Setting up monitoring..."
tee monitor.sh > /dev/null <<'EOF'
#!/bin/bash
# Simple monitoring script for ManageIt

check_service() {
    if docker-compose -f docker-compose.prod.yml ps $1 | grep -q "Up"; then
        echo "✅ $1 is running"
    else
        echo "❌ $1 is down"
        docker-compose -f docker-compose.prod.yml restart $1
    fi
}

echo "🔍 Checking ManageIt services..."
check_service app
check_service db
check_service redis
check_service nginx

# Check disk space
disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $disk_usage -gt 80 ]; then
    echo "⚠️ Disk usage is ${disk_usage}%"
fi

# Check memory usage
memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $memory_usage -gt 80 ]; then
    echo "⚠️ Memory usage is ${memory_usage}%"
fi

echo "✅ Monitoring check complete"
EOF

chmod +x monitor.sh

# Setup cron job for monitoring
(crontab -l 2>/dev/null; echo "*/5 * * * * $(pwd)/monitor.sh >> $(pwd)/logs/monitor.log 2>&1") | crontab -

echo "✅ Monitoring configured"

# Final instructions
echo ""
echo "🎉 ManageIt Production Deployment Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Update your domain in nginx.conf and docker-compose.prod.yml"
echo "2. Get proper SSL certificates: sudo certbot --nginx -d your-domain.com"
echo "3. Update the default admin password in the database"
echo "4. Configure your firewall to allow ports 80 and 443"
echo "5. Set up database backups"
echo ""
echo "🔗 Access your application:"
echo "   HTTP:  http://localhost"
echo "   HTTPS: https://localhost"
echo "   Health: http://localhost:8000/health"
echo ""
echo "📊 Monitoring:"
echo "   Logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "   Status: docker-compose -f docker-compose.prod.yml ps"
echo "   Monitor: ./monitor.sh"
echo ""
echo "🔒 Security Reminders:"
echo "   - Change default admin password"
echo "   - Review and update .env.production"
echo "   - Set up regular database backups"
echo "   - Monitor security logs"
echo ""
