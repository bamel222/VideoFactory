-- Migration 0001: initial schema (Supabase/Postgres)
-- Mirrors the SQLAlchemy models for the production database.

create extension if not exists "pgcrypto";

create table if not exists workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  owner_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  name text not null default '',
  hashed_password text not null,
  role text not null default 'reviewer' check (role in ('owner','admin','reviewer')),
  active boolean not null default true,
  workspace_id uuid references workspaces(id) not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists providers (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id) not null,
  name text not null,
  role text not null,
  endpoint text not null default '',
  api_key_encrypted text not null default '',
  quota_total int not null default 0,
  quota_used int not null default 0,
  cost_per_unit float not null default 0,
  priority int not null default 100,
  status text not null default 'active',
  languages jsonb not null default '[]',
  formats jsonb not null default '[]',
  limits jsonb not null default '{}',
  model text not null default '',
  avg_speed text not null default '',
  quality_estimate int not null default 50,
  healthy boolean not null default true,
  last_healthcheck_at text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists storage_backends (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id) not null,
  name text not null,
  kind text not null,
  config_encrypted text not null default '',
  priority int not null default 100,
  quota_bytes bigint not null default 0,
  used_bytes bigint not null default 0,
  cost_per_gb float not null default 0,
  status text not null default 'active',
  region text not null default '',
  replication text not null default '',
  healthy boolean not null default true,
  last_healthcheck_at text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists series (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id) not null,
  title text not null,
  topic text not null default '',
  kind text not null default 'documentary',
  status text not null default 'planned',
  planned_episodes int not null default 1,
  language text not null default 'fr',
  continuity_pack_id uuid,
  business_score float not null default 0,
  production_cost float not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists continuity_packs (
  id uuid primary key default gen_random_uuid(),
  series_id uuid references series(id) not null,
  name text not null default '',
  characters jsonb not null default '[]',
  voices jsonb not null default '[]',
  style jsonb not null default '{}',
  palette jsonb not null default '[]',
  lut text not null default '',
  decors jsonb not null default '[]',
  sfx jsonb not null default '[]',
  music jsonb not null default '{}',
  prompts jsonb not null default '{}',
  validated_frames jsonb not null default '[]',
  negative_rules jsonb not null default '[]',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists episodes (
  id uuid primary key default gen_random_uuid(),
  series_id uuid references series(id) not null,
  number int not null default 1,
  title text not null default '',
  status text not null default 'planned',
  is_final boolean not null default false,
  target_duration_seconds int not null default 90,
  script text,
  narration text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists scenes (
  id uuid primary key default gen_random_uuid(),
  episode_id uuid references episodes(id) not null,
  "order" int not null default 0,
  title text not null default '',
  description text not null default '',
  duration_seconds int not null default 10,
  beat text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists segments (
  id uuid primary key default gen_random_uuid(),
  scene_id uuid references scenes(id) not null,
  "order" int not null default 0,
  duration_seconds int not null default 8,
  content_type text not null default 'visual',
  prompt text not null default '',
  generated_content text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists job_runs (
  id uuid primary key default gen_random_uuid(),
  series_id uuid references series(id) not null,
  kind text not null default 'pipeline',
  status text not null default 'pending',
  dry_run boolean not null default false,
  error text not null default '',
  total_tasks int not null default 0,
  done_tasks int not null default 0,
  total_cost float not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists job_tasks (
  id uuid primary key default gen_random_uuid(),
  job_run_id uuid references job_runs(id) not null,
  series_id uuid references series(id),
  episode_id uuid references episodes(id),
  scene_id uuid references scenes(id),
  segment_id uuid references segments(id),
  task_type text not null,
  queue text not null,
  status text not null default 'pending',
  payload jsonb not null default '{}',
  result jsonb not null default '{}',
  error text not null default '',
  attempts int not null default 0,
  cost float not null default 0,
  provider_id uuid,
  checkpoint_id uuid,
  depends_on jsonb not null default '[]',
  sequence int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists checkpoints (
  id uuid primary key default gen_random_uuid(),
  task_id uuid,
  series_id uuid,
  scene_id uuid,
  kind text not null default 'text',
  content_ref text not null default '',
  provider text not null default '',
  prompt text not null default '',
  cost float not null default 0,
  hash text not null default '',
  storage_id uuid,
  metadata jsonb not null default '{}',
  version int not null default 1,
  previous_id uuid,
  valid boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists budget_forecasts (
  id uuid primary key default gen_random_uuid(),
  series_id uuid references series(id) not null,
  minutes_video float not null default 0,
  tts_chars int not null default 0,
  translations int not null default 0,
  storage_gb float not null default 0,
  gpu_hours float not null default 0,
  estimated_cost float not null default 0,
  quotas_ok boolean not null default true,
  risks jsonb not null default '[]',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists dry_runs (
  id uuid primary key default gen_random_uuid(),
  series_id uuid references series(id) not null,
  report jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists assets (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id) not null,
  storage_id uuid references storage_backends(id) not null,
  path text not null,
  checksum text not null default '',
  size bigint not null default 0,
  kind text not null default 'file',
  content_type text not null default '',
  public boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists licence_records (
  id uuid primary key default gen_random_uuid(),
  series_id uuid references series(id),
  asset_ref text not null default '',
  kind text not null default 'source',
  origin text not null default '',
  license text not null default 'unknown',
  usage text not null default '',
  source_url text not null default '',
  risk text not null default 'ok',
  file_path text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists review_records (
  id uuid primary key default gen_random_uuid(),
  episode_id uuid references episodes(id) not null,
  version int not null default 1,
  user_id uuid references users(id) not null,
  status text not null default 'revision',
  comment text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists seo_packages (
  id uuid primary key default gen_random_uuid(),
  episode_id uuid references episodes(id) not null,
  language text not null default 'fr',
  title text not null default '',
  description text not null default '',
  tags jsonb not null default '[]',
  hashtags jsonb not null default '[]',
  chapters jsonb not null default '[]',
  thumbnail text not null default '',
  keywords jsonb not null default '[]',
  metadata_json text not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists shorts_packages (
  id uuid primary key default gen_random_uuid(),
  episode_id uuid references episodes(id) not null,
  platform text not null default 'youtube',
  captions text not null default '',
  cta text not null default '',
  metadata_json text not null default '{}',
  asset_path text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ab_test_variants (
  id uuid primary key default gen_random_uuid(),
  episode_id uuid references episodes(id) not null,
  field text not null default 'title',
  variant text not null default '',
  score float not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists audit_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  action text not null,
  resource text not null,
  resource_id text,
  details_json text not null default '',
  ip text not null default '',
  user_agent text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
