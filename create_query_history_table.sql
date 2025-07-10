-- Create query_history table for storing user query history
CREATE TABLE IF NOT EXISTS query_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    db_name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    query TEXT,
    natural_language TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_db (user_id, db_name),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add foreign key constraint to link with users table
ALTER TABLE query_history ADD CONSTRAINT fk_query_history_user 
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE; 