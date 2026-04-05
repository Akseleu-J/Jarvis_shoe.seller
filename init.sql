-- Запусти этот файл в Supabase SQL Editor

CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY, brand TEXT, category TEXT, price INTEGER,
    material TEXT, color TEXT, city TEXT, wa_link TEXT, description TEXT,
    seller_name TEXT, photo_url TEXT, sizes TEXT, partner_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY, username TEXT,
    first_name TEXT, last_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS partners (
    id SERIAL PRIMARY KEY, name TEXT NOT NULL, contact_info TEXT,
    is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS partner_stocks (
    id SERIAL PRIMARY KEY,
    partner_id INTEGER REFERENCES partners(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 0, updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS waiting_list (
    id SERIAL PRIMARY KEY, user_id BIGINT, category TEXT,
    size TEXT, city TEXT, brand TEXT, timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS logs_general (
    id SERIAL PRIMARY KEY, user_id BIGINT, city TEXT, requested_size TEXT,
    query_text TEXT, action_type TEXT, seller_name TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS logs_search_requests (
    id SERIAL PRIMARY KEY, user_id BIGINT, query_text TEXT,
    requested_size TEXT, timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reviews_service (
    id SERIAL PRIMARY KEY, user_id BIGINT,
    review_text TEXT, timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reviews_product (
    id SERIAL PRIMARY KEY, user_id BIGINT,
    review_text TEXT, timestamp TIMESTAMP DEFAULT NOW()
);
