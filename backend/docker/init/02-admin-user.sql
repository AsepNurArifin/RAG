-- EnterpriseMind AI — Default Admin User
-- Insert default admin (password: admin123)
-- bcrypt hash of 'admin123'
INSERT INTO users (email, full_name, password_hash, role, is_active, department, clearance_level)
VALUES (
    'admin@enterprisemind.com',
    'System Admin',
    '$2b$12$jPujZjCoz5UnqCWgquxRIe1.X7YnaHhrUTp8Y9LJFSV0kTtWnzL/i',
    'admin',
    true,
    'IT',
    5
) ON CONFLICT (email) DO NOTHING;
