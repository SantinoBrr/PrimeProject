-- ============================================================
-- StyleSense — Database Schema
-- Ejecutar en: Supabase SQL Editor
-- ============================================================

-- ─── Tablas ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_profiles (
  id             UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name      TEXT,
  age            INTEGER CHECK (age >= 10 AND age <= 100),
  country        TEXT,
  city           TEXT,
  hair_type      TEXT CHECK (hair_type IN ('straight', 'wavy', 'curly', 'coily', 'kinky')),
  hair_density   TEXT CHECK (hair_density IN ('fine', 'medium', 'thick')) DEFAULT 'medium',
  hair_growth_direction TEXT CHECK (hair_growth_direction IN ('upward', 'sideways', 'downward', 'forward', 'mixed')),
  style_preference TEXT CHECK (style_preference IN ('classic', 'modern', 'casual', 'professional', 'edgy', 'streetwear', 'mixed')),
  maintenance_level TEXT CHECK (maintenance_level IN ('low', 'medium', 'high')) DEFAULT 'medium',
  lifestyle      TEXT CHECK (lifestyle IN ('active', 'office', 'creative', 'student', 'mixed')) DEFAULT 'mixed',
  additional_notes TEXT,
  face_shape     TEXT,
  profile_complete BOOLEAN DEFAULT FALSE,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hair_analyses (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  face_image_url TEXT NOT NULL,
  face_shape     TEXT,
  face_features  JSONB,
  analysis_text  TEXT,
  recommendations JSONB,
  haircuts_to_avoid JSONB,
  styling_tips   TEXT,
  overall_advice TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS haircut_results (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  analysis_id     UUID REFERENCES hair_analyses(id) ON DELETE SET NULL,
  selected_haircut TEXT NOT NULL,
  result_image_url TEXT NOT NULL,
  feedback        JSONB,
  score           NUMERIC(3,1) CHECK (score >= 0 AND score <= 10),
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Indexes ─────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_hair_analyses_user_id ON hair_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_hair_analyses_created ON hair_analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_haircut_results_user_id ON haircut_results(user_id);
CREATE INDEX IF NOT EXISTS idx_haircut_results_created ON haircut_results(created_at DESC);

-- ─── Auto-update updated_at ───────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_updated_at ON user_profiles;
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─── Row Level Security ───────────────────────────────────────

ALTER TABLE user_profiles    ENABLE ROW LEVEL SECURITY;
ALTER TABLE hair_analyses    ENABLE ROW LEVEL SECURITY;
ALTER TABLE haircut_results  ENABLE ROW LEVEL SECURITY;

-- user_profiles
CREATE POLICY "profile_select" ON user_profiles
  FOR SELECT USING (auth.uid() = id);
CREATE POLICY "profile_insert" ON user_profiles
  FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "profile_update" ON user_profiles
  FOR UPDATE USING (auth.uid() = id);

-- hair_analyses
CREATE POLICY "analysis_select" ON hair_analyses
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "analysis_insert" ON hair_analyses
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- haircut_results
CREATE POLICY "results_select" ON haircut_results
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "results_insert" ON haircut_results
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ─── Storage Buckets ──────────────────────────────────────────
-- Ejecutar esto también en la sección Storage de Supabase

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
  ('face-images',     'face-images',     false, 10485760, ARRAY['image/jpeg','image/png','image/webp']),
  ('haircut-results', 'haircut-results', false, 10485760, ARRAY['image/jpeg','image/png','image/webp'])
ON CONFLICT (id) DO NOTHING;

-- Storage policies: usuarios solo pueden acceder a su propia carpeta
CREATE POLICY "face_images_upload" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'face-images' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "face_images_select" ON storage.objects
  FOR SELECT TO authenticated
  USING (bucket_id = 'face-images' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "face_images_delete" ON storage.objects
  FOR DELETE TO authenticated
  USING (bucket_id = 'face-images' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "results_upload" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'haircut-results' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "results_select" ON storage.objects
  FOR SELECT TO authenticated
  USING (bucket_id = 'haircut-results' AND (storage.foldername(name))[1] = auth.uid()::text);
