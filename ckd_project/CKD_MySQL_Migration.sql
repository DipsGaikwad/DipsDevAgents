-- Back up ckd_project before running. Run in MySQL Workbench/phpMyAdmin.
USE ckd_project;

-- 1) Existing patients table stores source_patient_id but no patient's display name.
-- The Add Patient form needs a place to store that name. This is additive and keeps old rows.
ALTER TABLE patients ADD COLUMN full_name VARCHAR(150) NULL;

-- 2) Store per-user hospital/profile setting, because current users table has no hospital field.
CREATE TABLE user_profile_settings (
    user_id BIGINT UNSIGNED PRIMARY KEY,
    hospital VARCHAR(255) NULL,
    CONSTRAINT fk_profile_settings_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 3) In-app notifications must persist for each account, not just show a fake toast.
CREATE TABLE notifications (
    notification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    patient_id VARCHAR(20) NULL,
    title VARCHAR(180) NOT NULL,
    message VARCHAR(1000) NOT NULL,
    notification_type VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notifications_user_created(user_id, created_at),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE SET NULL
);

-- 4) Resource metadata is stored here. Original document bytes are stored under RESOURCE_DIR.
CREATE TABLE knowledge_resources (
    resource_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(80) NOT NULL,
    source_name VARCHAR(255) NULL,
    source_url VARCHAR(1000) NULL,
    version_label VARCHAR(100) NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL UNIQUE,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT UNSIGNED NOT NULL,
    uploaded_by BIGINT UNSIGNED NOT NULL,
    status ENUM('UPLOADED','PROCESSING','INDEXED','FAILED') NOT NULL DEFAULT 'UPLOADED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_resource_category_created(category, created_at),
    CONSTRAINT fk_resource_uploader FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
);

-- Confirm tables and the display-name field exist afterwards.
SHOW TABLES;
DESCRIBE patients;
DESCRIBE users;
