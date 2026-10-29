-- =========================================================
-- CiviQ Database Schema
-- Backend + AI + Complaint Management
-- =========================================================

CREATE DATABASE IF NOT EXISTS civiq;

USE civiq;


-- =========================================================
-- 1. DEPARTMENTS
-- =========================================================

CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- 2. USERS
-- Citizen / Admin / Officer
-- =========================================================

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    email VARCHAR(150) NOT NULL UNIQUE,

    password_hash VARCHAR(255) NOT NULL,

    phone VARCHAR(20),

    role ENUM('CITIZEN', 'ADMIN', 'OFFICER') NOT NULL,

    department_id INT NULL,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(id)
        ON DELETE SET NULL
);


-- =========================================================
-- 3. COMPLAINTS
-- Main complaint + AI prediction
-- =========================================================

CREATE TABLE IF NOT EXISTS complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,

    citizen_id INT NOT NULL,

    title VARCHAR(200) NOT NULL,

    description TEXT NOT NULL,

    category VARCHAR(100),

    priority ENUM(
        'LOW',
        'MEDIUM',
        'HIGH',
        'CRITICAL'
    ) DEFAULT 'MEDIUM',

    department_id INT NULL,

    status ENUM(
        'PENDING',
        'ASSIGNED',
        'IN_PROGRESS',
        'RESOLVED',
        'CONFIRMED',
        'REOPENED',
        'CLOSED'
    ) DEFAULT 'PENDING',

    ai_confidence DECIMAL(5,4),

    ai_category VARCHAR(100),

    ai_department VARCHAR(100),

    latitude DECIMAL(10,8),

    longitude DECIMAL(11,8),

    address VARCHAR(500),

    citizen_confirmed BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    resolved_at TIMESTAMP NULL,

    confirmed_at TIMESTAMP NULL,

    FOREIGN KEY (citizen_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (department_id)
        REFERENCES departments(id)
        ON DELETE SET NULL
);


-- =========================================================
-- 4. COMPLAINT ASSIGNMENTS
-- Which officer is assigned to which complaint
-- =========================================================

CREATE TABLE IF NOT EXISTS complaint_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,

    complaint_id INT NOT NULL,

    officer_id INT NOT NULL,

    assigned_by INT NOT NULL,

    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    is_current BOOLEAN DEFAULT TRUE,

    FOREIGN KEY (complaint_id)
        REFERENCES complaints(id)
        ON DELETE CASCADE,

    FOREIGN KEY (officer_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (assigned_by)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- =========================================================
-- 5. COMPLAINT STATUS HISTORY
-- Tracks every status change
-- =========================================================

CREATE TABLE IF NOT EXISTS complaint_status_history (
    id INT AUTO_INCREMENT PRIMARY KEY,

    complaint_id INT NOT NULL,

    old_status VARCHAR(50),

    new_status VARCHAR(50) NOT NULL,

    changed_by INT NOT NULL,

    remarks VARCHAR(500),

    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id)
        REFERENCES complaints(id)
        ON DELETE CASCADE,

    FOREIGN KEY (changed_by)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- =========================================================
-- 6. COMPLAINT MEDIA
-- Complaint photo / resolution photo
-- =========================================================

CREATE TABLE IF NOT EXISTS complaint_media (
    id INT AUTO_INCREMENT PRIMARY KEY,

    complaint_id INT NOT NULL,

    uploaded_by INT NOT NULL,

    media_type ENUM(
        'COMPLAINT_PHOTO',
        'RESOLUTION_PHOTO',
        'OTHER'
    ) NOT NULL,

    file_url VARCHAR(500) NOT NULL,

    description VARCHAR(255),

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id)
        REFERENCES complaints(id)
        ON DELETE CASCADE,

    FOREIGN KEY (uploaded_by)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- =========================================================
-- 7. RESOLUTIONS
-- Officer resolution details
-- =========================================================

CREATE TABLE IF NOT EXISTS resolutions (
    id INT AUTO_INCREMENT PRIMARY KEY,

    complaint_id INT NOT NULL,

    officer_id INT NOT NULL,

    resolution_text TEXT NOT NULL,

    resolution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id)
        REFERENCES complaints(id)
        ON DELETE CASCADE,

    FOREIGN KEY (officer_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- =========================================================
-- 8. NOTIFICATIONS
-- Citizen / Admin / Officer notifications
-- =========================================================

CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    complaint_id INT NULL,

    title VARCHAR(200) NOT NULL,

    message TEXT NOT NULL,

    notification_type VARCHAR(50),

    is_read BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (complaint_id)
        REFERENCES complaints(id)
        ON DELETE CASCADE
);


-- =========================================================
-- CHECK TABLES
-- =========================================================

SHOW TABLES;