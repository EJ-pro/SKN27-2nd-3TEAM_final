CREATE DATABASE IF NOT EXISTS churn_db;
USE churn_db;

CREATE TABLE IF NOT EXISTS members (
    msno VARCHAR(50) PRIMARY KEY,
    is_churn INT,
    city INT,
    bd INT,
    gender VARCHAR(20),
    registered_via INT,
    registration_init_time DATE
);

CREATE TABLE IF NOT EXISTS transactions (
    id INT PRIMARY KEY,
    msno VARCHAR(50) NOT NULL,
    payment_method_id INT,
    payment_plan_days INT,
    plan_list_price INT,
    actual_amount_paid INT,
    is_auto_renew INT,
    transaction_date DATE,
    membership_expire_date DATE,
    is_cancel INT,
    CONSTRAINT fk_transactions_members
    FOREIGN KEY (msno) REFERENCES members(msno)
);

CREATE TABLE IF NOT EXISTS user_logs (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    msno VARCHAR(50) NOT NULL,
    log_date DATE,
    num_25 INT,
    num_50 INT,
    num_75 INT,
    num_100 INT,
    CONSTRAINT fk_user_logs_members
    FOREIGN KEY (msno) REFERENCES members(msno)
);

CREATE TABLE IF NOT EXISTS churn_predictions (
    prediction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    msno VARCHAR(50) NOT NULL,
    prediction_date DATE NOT NULL,
    churn_probability DECIMAL(6,4) NOT NULL,
    risk_grade VARCHAR(30),
    main_reason_code VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_predictions_members
    FOREIGN KEY (msno) REFERENCES members(msno)
);

CREATE TABLE IF NOT EXISTS action_history (
    action_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    msno VARCHAR(50) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_detail VARCHAR(100),
    action_date DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_actions_members
    FOREIGN KEY (msno) REFERENCES members(msno)
);