/*
  # User Profiles and Platform Schema

  1. New Tables
    - `user_profiles`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key to auth.users)
      - `full_name` (text)
      - `phone` (text)
      - `date_of_birth` (date)
      - `location` (text)
      - `school` (text)
      - `current_class` (text)
      - `stream` (text)
      - `interests` (text array)
      - `career_goals` (text)
      - `created_at` (timestamp)
      - `updated_at` (timestamp)

    - `quiz_results`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `quiz_type` (text)
      - `answers` (jsonb)
      - `results` (jsonb)
      - `completed_at` (timestamp)

    - `user_colleges`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `college_name` (text)
      - `college_id` (text)
      - `status` (text) - saved, applied, admitted
      - `created_at` (timestamp)

    - `timeline_events`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `title` (text)
      - `description` (text)
      - `event_date` (timestamp)
      - `category` (text)
      - `status` (text)
      - `reminder_set` (boolean)
      - `created_at` (timestamp)

  2. Security
    - Enable RLS on all tables
    - Add policies for authenticated users to manage their own data
*/

-- User Profiles Table
CREATE TABLE IF NOT EXISTS user_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name text NOT NULL DEFAULT '',
  phone text DEFAULT '',
  date_of_birth date,
  location text DEFAULT '',
  school text DEFAULT '',
  current_class text DEFAULT '',
  stream text DEFAULT '',
  interests text[] DEFAULT '{}',
  career_goals text DEFAULT '',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id)
);

-- Quiz Results Table
CREATE TABLE IF NOT EXISTS quiz_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  quiz_type text NOT NULL DEFAULT 'aptitude',
  answers jsonb NOT NULL DEFAULT '{}',
  results jsonb NOT NULL DEFAULT '{}',
  completed_at timestamptz DEFAULT now()
);

-- User Colleges Table
CREATE TABLE IF NOT EXISTS user_colleges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  college_name text NOT NULL,
  college_id text DEFAULT '',
  status text DEFAULT 'saved' CHECK (status IN ('saved', 'applied', 'admitted', 'rejected')),
  created_at timestamptz DEFAULT now()
);

-- Timeline Events Table
CREATE TABLE IF NOT EXISTS timeline_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL,
  description text DEFAULT '',
  event_date timestamptz NOT NULL,
  category text DEFAULT 'general' CHECK (category IN ('exam', 'admission', 'scholarship', 'deadline', 'general')),
  status text DEFAULT 'upcoming' CHECK (status IN ('upcoming', 'completed', 'urgent', 'missed')),
  reminder_set boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_colleges ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_profiles
CREATE POLICY "Users can view own profile"
  ON user_profiles
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
  ON user_profiles
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
  ON user_profiles
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- RLS Policies for quiz_results
CREATE POLICY "Users can view own quiz results"
  ON quiz_results
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own quiz results"
  ON quiz_results
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- RLS Policies for user_colleges
CREATE POLICY "Users can manage own college list"
  ON user_colleges
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id);

-- RLS Policies for timeline_events
CREATE POLICY "Users can manage own timeline events"
  ON timeline_events
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_results_user_id ON quiz_results(user_id);
CREATE INDEX IF NOT EXISTS idx_user_colleges_user_id ON user_colleges(user_id);
CREATE INDEX IF NOT EXISTS idx_timeline_events_user_id ON timeline_events(user_id);
CREATE INDEX IF NOT EXISTS idx_timeline_events_date ON timeline_events(event_date);

-- Function to automatically create user profile
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.user_profiles (user_id, full_name)
  VALUES (new.id, COALESCE(new.raw_user_meta_data->>'full_name', ''));
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on user signup
CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();