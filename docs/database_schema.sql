-- ============================================================================
-- HealthOS AI Database Schema for Supabase
-- ============================================================================
-- Comprehensive schema design for all features including:
-- - User management and authentication
-- - Health profiles and metrics
-- - Meal planning and nutrition
-- - Feedback and learning
-- - Analytics and events
-- - A/B testing and experiments
-- - User segmentation
-- - Churn prediction features
--
-- Generated for PostgreSQL on Supabase.
-- Run these SQL commands to initialize the database.
-- ============================================================================

-- ============================================================================
-- USERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    username   TEXT        UNIQUE NOT NULL,
    password   TEXT        NOT NULL,   -- bcrypt hash
    created_at TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);

-- ============================================================================
-- PROFILES (user health & survey data)
-- ============================================================================

CREATE TABLE IF NOT EXISTS profiles (
    id           UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- survey / goal fields (all optional, stored as-is from the frontend)
    age          TEXT,
    gender       TEXT,
    height       TEXT,
    weight       TEXT,
    goal         TEXT,
    dietary_pref TEXT,
    workout_times TEXT,
    UNIQUE (user_id)
);

CREATE INDEX idx_profiles_user_id ON profiles(user_id);

-- ============================================================================
-- CHAT LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS chat_logs (
    id         UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT      NOT NULL,   -- 'user' | 'assistant'
    content    TEXT      NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_logs_user_id ON chat_logs(user_id);
CREATE INDEX idx_chat_logs_created_at ON chat_logs(user_id, created_at);

-- ============================================================================
-- HEALTH METRICS (Time Series)
-- ============================================================================

CREATE TABLE IF NOT EXISTS health_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    metric_date DATE,
    weight DECIMAL(6, 2),
    body_fat_percent DECIMAL(5, 2),
    blood_pressure_systolic INTEGER,
    blood_pressure_diastolic INTEGER,
    heart_rate INTEGER,
    blood_glucose INTEGER,
    sleep_hours DECIMAL(4, 2),
    stress_level INTEGER,
    mood INTEGER,
    energy_level INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_health_metrics_user_id_date ON health_metrics(user_id, metric_date);
CREATE INDEX idx_health_metrics_user_id ON health_metrics(user_id);

-- ============================================================================
-- MEALS (User meal logs — used by the CampusFuel API)
-- Each row is one logged meal for a user. `items` and `total` are stored as
-- JSONB so the full food-item list and macro totals are preserved.
-- ============================================================================

CREATE TABLE IF NOT EXISTS meals (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        TEXT        NOT NULL,           -- Breakfast | Lunch | Dinner | Snack
    time        TEXT,                           -- HH:MM display string
    date        DATE        NOT NULL,           -- local calendar date
    timestamp   TEXT,                           -- ISO-8601 for ordering
    items       JSONB       NOT NULL DEFAULT '[]'::jsonb,  -- [{name,calories,protein,carbs,fat}]
    total       JSONB       NOT NULL DEFAULT '{}'::jsonb   -- {calories,protein,carbs,fat}
);

CREATE INDEX idx_meals_user_id        ON meals(user_id);
CREATE INDEX idx_meals_user_date      ON meals(user_id, date);
CREATE INDEX idx_meals_timestamp      ON meals(timestamp);

-- ============================================================================
-- HEALTH GOALS AND TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS health_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    goal_name VARCHAR(255) NOT NULL,
    goal_type VARCHAR(50),
    target_value DECIMAL(10, 2),
    current_value DECIMAL(10, 2),
    unit VARCHAR(50),
    start_date DATE,
    target_date DATE,
    status VARCHAR(50) DEFAULT 'active',
    progress_percentage DECIMAL(5, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_health_goals_user_id ON health_goals(user_id);
CREATE INDEX idx_health_goals_status ON health_goals(status);

-- ============================================================================
-- WORKOUTS AND ACTIVITY
-- ============================================================================

CREATE TABLE IF NOT EXISTS workouts (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        TEXT    NOT NULL,           -- e.g. Strength Training, Cardio
    duration    INTEGER NOT NULL,           -- minutes
    notes       TEXT,
    date        DATE    NOT NULL,           -- local calendar date
    timestamp   TEXT                        -- ISO-8601 for ordering
);

CREATE INDEX idx_workouts_user_id_date ON workouts(user_id, date);
CREATE INDEX idx_workouts_user_id ON workouts(user_id);

-- ============================================================================
-- USER FEEDBACK AND LEARNING
-- ============================================================================

CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    feedback_type VARCHAR(50),
    rating INTEGER,
    content TEXT,
    reference_id UUID,
    reference_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_user_id ON feedback(user_id);
CREATE INDEX idx_feedback_status ON feedback(status);
CREATE INDEX idx_feedback_created_at ON feedback(created_at);

-- ============================================================================
-- ANALYTICS: USER EVENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id UUID,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_events_user_id ON user_events(user_id);
CREATE INDEX idx_user_events_event_type ON user_events(event_type);
CREATE INDEX idx_user_events_timestamp ON user_events(event_timestamp);
CREATE INDEX idx_user_events_user_id_timestamp ON user_events(user_id, event_timestamp);

-- ============================================================================
-- A/B TESTING: EXPERIMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    metric_name VARCHAR(100),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_experiments_created_at ON experiments(created_at);

-- ============================================================================
-- A/B TESTING: EXPERIMENT VARIANTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS experiment_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
    variant_name VARCHAR(255),
    description TEXT,
    weight DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_experiment_variants_experiment_id ON experiment_variants(experiment_id);

-- ============================================================================
-- A/B TESTING: VARIANT ASSIGNMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS variant_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES experiment_variants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_variant_assignments_experiment_id ON variant_assignments(experiment_id);
CREATE INDEX idx_variant_assignments_user_id ON variant_assignments(user_id);
CREATE UNIQUE INDEX idx_variant_assignments_unique ON variant_assignments(experiment_id, user_id);

-- ============================================================================
-- A/B TESTING: EXPERIMENT RESULTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS experiment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES experiment_variants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    metric_value DECIMAL(10, 4),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_experiment_results_experiment_id ON experiment_results(experiment_id);
CREATE INDEX idx_experiment_results_variant_id ON experiment_results(variant_id);
CREATE INDEX idx_experiment_results_user_id ON experiment_results(user_id);

-- ============================================================================
-- USER SEGMENTATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    segment_type VARCHAR(50),
    segment_name VARCHAR(255),
    segment_value VARCHAR(255),
    confidence_score DECIMAL(5, 2),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_segments_user_id ON user_segments(user_id);
CREATE INDEX idx_user_segments_segment_type ON user_segments(segment_type);

-- ============================================================================
-- CHURN PREDICTION: USER FEATURES
-- ============================================================================

CREATE TABLE IF NOT EXISTS churn_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    days_since_last_login INTEGER,
    login_frequency DECIMAL(6, 2),
    goals_completion_rate DECIMAL(5, 2),
    meal_adherence_rate DECIMAL(5, 2),
    feedback_frequency DECIMAL(6, 2),
    activity_consistency DECIMAL(5, 2),
    profile_completion_percent INTEGER,
    health_check_frequency DECIMAL(6, 2),
    churn_risk_score DECIMAL(5, 4),
    churn_risk_level VARCHAR(50),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_churn_features_user_id ON churn_features(user_id);
CREATE INDEX idx_churn_features_churn_risk_level ON churn_features(churn_risk_level);
CREATE INDEX idx_churn_features_updated_at ON churn_features(updated_at);

-- ============================================================================
-- CHURN PREDICTION: AT-RISK INTERVENTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS churn_interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    intervention_type VARCHAR(100),
    recommended_action VARCHAR(255),
    sent_at TIMESTAMP,
    response_received_at TIMESTAMP,
    response_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_churn_interventions_user_id ON churn_interventions(user_id);
CREATE INDEX idx_churn_interventions_created_at ON churn_interventions(created_at);

-- ============================================================================
-- RECOMMENDATIONS CACHE
-- ============================================================================

CREATE TABLE IF NOT EXISTS recommendation_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    recommendation_type VARCHAR(100),
    content_id UUID,
    score DECIMAL(5, 4),
    rank INTEGER,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recommendation_cache_user_id ON recommendation_cache(user_id);
CREATE INDEX idx_recommendation_cache_expires_at ON recommendation_cache(expires_at);

-- ============================================================================
-- SYSTEM LOGS AND MONITORING
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    log_level VARCHAR(50),
    service_name VARCHAR(100),
    message TEXT,
    error_details JSONB,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX idx_system_logs_log_level ON system_logs(log_level);
CREATE INDEX idx_system_logs_service_name ON system_logs(service_name);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE workouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE churn_features ENABLE ROW LEVEL SECURITY;

-- Note: Auth policies should be configured in Supabase UI
-- These are templates - adjust based on your auth setup

CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (true);

-- Allow anyone (anon) to create a new account via signup
CREATE POLICY "Allow public signup" ON users
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (true);

-- Health profiles
CREATE POLICY "Users can view own health profile" ON health_profiles
    FOR SELECT USING (true);

CREATE POLICY "Users can update own health profile" ON health_profiles
    FOR UPDATE USING (true);

-- Health metrics
CREATE POLICY "Users can view own metrics" ON health_metrics
    FOR SELECT USING (true);

CREATE POLICY "Users can insert own metrics" ON health_metrics
    FOR INSERT WITH CHECK (true);

-- Meal logs
CREATE POLICY "Users can view own meal logs" ON meal_logs
    FOR SELECT USING (true);

CREATE POLICY "Users can insert own meal logs" ON meal_logs
    FOR INSERT WITH CHECK (true);

-- ============================================================================
-- STORED PROCEDURES AND FUNCTIONS
-- ============================================================================

-- Function to calculate user's BMR (Basal Metabolic Rate)
CREATE OR REPLACE FUNCTION calculate_bmr(age INT, gender VARCHAR, height DECIMAL, weight DECIMAL)
RETURNS DECIMAL AS $$
DECLARE
    bmr DECIMAL;
BEGIN
    IF gender = 'male' THEN
        bmr := 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age);
    ELSE
        bmr := 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age);
    END IF;
    RETURN ROUND(bmr, 2);
END;
$$ LANGUAGE plpgsql;

-- Function to get user meal adherence for a date range
CREATE OR REPLACE FUNCTION get_meal_adherence(user_id UUID, start_date DATE, end_date DATE)
RETURNS DECIMAL AS $$
DECLARE
    avg_adherence DECIMAL;
BEGIN
    SELECT AVG(adherence_score) INTO avg_adherence FROM meal_logs
    WHERE meal_logs.user_id = $1
    AND logged_date BETWEEN $2 AND $3;
    
    RETURN COALESCE(avg_adherence, 0);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- User summary view
CREATE OR REPLACE VIEW user_summary AS
SELECT
    u.id,
    u.email,
    u.name,
    u.created_at,
    u.last_login,
    hp.age,
    hp.weight,
    hp.height,
    hp.profile_completion_percent,
    COUNT(DISTINCT ml.id) as total_meals_logged,
    COUNT(DISTINCT hg.id) as total_goals,
    COUNT(DISTINCT w.id) as total_workouts
FROM users u
LEFT JOIN health_profiles hp ON u.id = hp.user_id
LEFT JOIN meal_logs ml ON u.id = ml.user_id
LEFT JOIN health_goals hg ON u.id = hg.user_id
LEFT JOIN workouts w ON u.id = w.user_id
GROUP BY u.id, u.email, u.name, u.created_at, u.last_login, hp.age, hp.weight, hp.height, hp.profile_completion_percent;

-- User engagement view
CREATE OR REPLACE VIEW user_engagement AS
SELECT
    u.id,
    u.email,
    COUNT(DISTINCT ue.id) as total_events,
    COUNT(DISTINCT CASE WHEN ue.event_timestamp > NOW() - INTERVAL '7 days' THEN ue.id END) as events_last_7_days,
    COUNT(DISTINCT CASE WHEN ue.event_timestamp > NOW() - INTERVAL '30 days' THEN ue.id END) as events_last_30_days,
    MAX(ue.event_timestamp) as last_event_timestamp
FROM users u
LEFT JOIN user_events ue ON u.id = ue.user_id
GROUP BY u.id, u.email;

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- Sample meals
INSERT INTO meals (name, description, calories, protein, carbs, fats, fiber, preparation_time, difficulty_level, tags)
VALUES
    ('Grilled Chicken Breast with Vegetables', 'High-protein lean meal', 350, 45, 20, 8, 6, 25, 'easy', ARRAY['high-protein', 'low-carb', 'healthy']),
    ('Quinoa Buddha Bowl', 'Complete grain with vegetables', 420, 15, 65, 12, 8, 20, 'easy', ARRAY['vegetarian', 'vegan', 'gluten-free']),
    ('Salmon Fillet with Sweet Potato', 'Omega-3 rich meal', 480, 40, 35, 18, 5, 30, 'medium', ARRAY['high-protein', 'omega-3', 'healthy'])
ON CONFLICT DO NOTHING;

-- ============================================================================
-- COMMENTS AND DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE users IS 'Core user account information and authentication';
COMMENT ON TABLE health_profiles IS 'User health profile, goals, and dietary preferences';
COMMENT ON TABLE health_metrics IS 'Time-series health measurements (weight, BP, HR, etc)';
COMMENT ON TABLE user_events IS 'User activity event log for analytics and engagement tracking';
COMMENT ON TABLE experiments IS 'A/B test experiments configuration';
COMMENT ON TABLE churn_features IS 'Calculated churn prediction features for each user';
