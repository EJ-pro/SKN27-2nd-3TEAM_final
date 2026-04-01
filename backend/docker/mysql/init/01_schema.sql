DROP DATABASE IF EXISTS churn_db;
CREATE DATABASE churn_db;
USE churn_db;

CREATE TABLE members (
    msno VARCHAR(50) NOT NULL,
    is_churn TINYINT NOT NULL,
    city INT DEFAULT NULL,
    bd INT DEFAULT NULL,
    gender VARCHAR(10) DEFAULT NULL,
    registered_via INT DEFAULT NULL,
    registration_init_time DATE DEFAULT NULL,
    PRIMARY KEY (msno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE transactions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    msno VARCHAR(50) NOT NULL,
    payment_method_id INT DEFAULT NULL,
    payment_plan_days INT DEFAULT NULL,
    plan_list_price INT DEFAULT NULL,
    actual_amount_paid INT DEFAULT NULL,
    is_auto_renew TINYINT DEFAULT NULL,
    transaction_date DATE DEFAULT NULL,
    membership_expire_date DATE DEFAULT NULL,
    is_cancel TINYINT DEFAULT NULL,
    PRIMARY KEY (id),
    KEY fk_transactions_members (msno),
    CONSTRAINT fk_transactions_members
        FOREIGN KEY (msno) REFERENCES members (msno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE user_logs (
    log_id BIGINT NOT NULL AUTO_INCREMENT,
    msno VARCHAR(50) NOT NULL,
    log_date DATE DEFAULT NULL,
    num_25 INT DEFAULT NULL,
    num_50 INT DEFAULT NULL,
    num_75 INT DEFAULT NULL,
    num_985 INT DEFAULT NULL,
    num_100 INT DEFAULT NULL,
    num_unq INT DEFAULT NULL,
    total_secs DOUBLE DEFAULT NULL,
    PRIMARY KEY (log_id),
    KEY fk_user_logs_members (msno),
    CONSTRAINT fk_user_logs_members
        FOREIGN KEY (msno) REFERENCES members (msno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;