-- Production Database Initialization Script
-- Run this script to set up the production database

CREATE DATABASE IF NOT EXISTS mess_management_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mess_management_prod;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'mess', 'admin') NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    mess_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_mess_id (mess_id)
);

-- Mess halls table
CREATE TABLE IF NOT EXISTS mess_halls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    capacity INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Menu items table
CREATE TABLE IF NOT EXISTS menu_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mess_id INT NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    category ENUM('breakfast', 'lunch', 'dinner', 'snacks') NOT NULL,
    meal_type ENUM('veg', 'non_veg') NOT NULL,
    price DECIMAL(10,2) DEFAULT 0.00,
    is_available BOOLEAN DEFAULT TRUE,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (mess_id) REFERENCES mess_halls(id) ON DELETE CASCADE,
    INDEX idx_mess_date (mess_id, date),
    INDEX idx_category (category),
    INDEX idx_meal_type (meal_type)
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    mess_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_type ENUM('monthly', 'daily', 'extra') NOT NULL,
    payment_method ENUM('cash', 'online', 'card') NOT NULL,
    transaction_id VARCHAR(100),
    status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
    payment_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (mess_id) REFERENCES mess_halls(id) ON DELETE CASCADE,
    INDEX idx_user_date (user_id, payment_date),
    INDEX idx_mess_date (mess_id, payment_date),
    INDEX idx_status (status)
);

-- Feedback table
CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    mess_id INT NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    food_quality_rating INT CHECK (food_quality_rating >= 1 AND food_quality_rating <= 5),
    service_rating INT CHECK (service_rating >= 1 AND service_rating <= 5),
    cleanliness_rating INT CHECK (cleanliness_rating >= 1 AND cleanliness_rating <= 5),
    comments TEXT,
    feedback_date DATE NOT NULL,
    is_anonymous BOOLEAN DEFAULT FALSE,
    status ENUM('pending', 'reviewed', 'resolved') DEFAULT 'pending',
    admin_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (mess_id) REFERENCES mess_halls(id) ON DELETE CASCADE,
    INDEX idx_mess_date (mess_id, feedback_date),
    INDEX idx_rating (rating),
    INDEX idx_status (status)
);

-- Waste tracking table
CREATE TABLE IF NOT EXISTS waste_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mess_id INT NOT NULL,
    date DATE NOT NULL,
    food_category ENUM('breakfast', 'lunch', 'dinner', 'snacks') NOT NULL,
    waste_amount DECIMAL(10,2) NOT NULL COMMENT 'in kg',
    total_prepared DECIMAL(10,2) NOT NULL COMMENT 'in kg',
    waste_percentage DECIMAL(5,2) GENERATED ALWAYS AS ((waste_amount / total_prepared) * 100) STORED,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (mess_id) REFERENCES mess_halls(id) ON DELETE CASCADE,
    INDEX idx_mess_date (mess_id, date),
    INDEX idx_category (food_category)
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('general', 'payment', 'menu', 'maintenance') DEFAULT 'general',
    target_role ENUM('all', 'student', 'mess', 'admin') DEFAULT 'all',
    mess_id INT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (mess_id) REFERENCES mess_halls(id) ON DELETE SET NULL,
    INDEX idx_target_role (target_role),
    INDEX idx_active_expires (is_active, expires_at)
);

-- User sessions table for security tracking
CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_token (user_id, session_token),
    INDEX idx_expires (expires_at)
);

-- Security logs table
CREATE TABLE IF NOT EXISTS security_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    user_id INT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    event_data JSON,
    severity ENUM('INFO', 'WARNING', 'ERROR', 'CRITICAL') DEFAULT 'INFO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_event_type (event_type),
    INDEX idx_severity (severity),
    INDEX idx_created_at (created_at)
);

-- Insert default mess halls
INSERT INTO mess_halls (name, location, capacity) VALUES
('Main Mess Hall', 'Central Campus', 500),
('North Campus Mess', 'North Campus', 300),
('South Campus Mess', 'South Campus', 250);

-- Insert default admin user (password: admin123 - CHANGE THIS!)
INSERT INTO users (username, email, password_hash, role, full_name, phone) VALUES
('admin', 'admin@manageit.com', 'scrypt:32768:8:1$YourHashedPasswordHere', 'admin', 'System Administrator', '+1234567890');

-- Create indexes for performance
CREATE INDEX idx_users_role_active ON users(role, is_active);
CREATE INDEX idx_payments_date_status ON payments(payment_date, status);
CREATE INDEX idx_feedback_date_rating ON feedback(feedback_date, rating);
CREATE INDEX idx_waste_date_percentage ON waste_tracking(date, waste_percentage);

-- Set up database user permissions (run as root)
-- CREATE USER 'manageit_prod'@'%' IDENTIFIED BY 'your_strong_password';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON mess_management_prod.* TO 'manageit_prod'@'%';
-- FLUSH PRIVILEGES;
