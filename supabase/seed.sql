-- Seed: workspace + roles + fake providers + local storage
insert into workspaces (id, name) values ('11111111-1111-1111-1111-111111111111', 'Video Factory AI');

-- Passwords are bcrypt hashes of "password123" (demo only)
insert into users (id, email, name, role, hashed_password, workspace_id) values
  ('22222222-2222-2222-2222-222222222222', 'owner@vf.ai', 'Owner', 'owner',
   '$2b$12$C6UzMDM.H6dfI/f/IKcEe.5Y7Dm4jS4mJqQh7k0VhKqQqQqQqQqQq', '11111111-1111-1111-1111-111111111111'),
  ('33333333-3333-3333-3333-333333333333', 'admin@vf.ai', 'Admin', 'admin',
   '$2b$12$C6UzMDM.H6dfI/f/IKcEe.5Y7Dm4jS4mJqQh7k0VhKqQqQqQqQqQq', '11111111-1111-1111-1111-111111111111'),
  ('44444444-4444-4444-4444-444444444444', 'reviewer@vf.ai', 'Reviewer', 'reviewer',
   '$2b$12$C6UzMDM.H6dfI/f/IKcEe.5Y7Dm4jS4mJqQh7k0VhKqQqQqQqQqQq', '11111111-1111-1111-1111-111111111111');

insert into providers (workspace_id, name, role, endpoint, quota_total, cost_per_unit, priority, status, languages, formats, model, quality_estimate) values
  ('11111111-1111-1111-1111-111111111111', 'Fake Research', 'research', 'mock://research', 100000, 0, 10, 'active', '["fr","en"]', '["text"]', 'fake', 60),
  ('11111111-1111-1111-1111-111111111111', 'Fake TTS', 'tts', 'mock://tts', 1000000, 0, 10, 'active', '["fr","en","es","de"]', '["mp3","wav"]', 'fake', 70),
  ('11111111-1111-1111-1111-111111111111', 'Fake Video', 'video', 'mock://video', 100000, 0, 10, 'active', '[]', '["mp4"]', 'fake', 55),
  ('11111111-1111-1111-1111-111111111111', 'Fake Image', 'image', 'mock://image', 100000, 0, 10, 'active', '[]', '["png"]', 'fake', 55),
  ('11111111-1111-1111-1111-111111111111', 'Fake Translate', 'translation', 'mock://translation', 1000000, 0, 10, 'active', '["fr","en","es","de"]', '["text"]', 'fake', 70),
  ('11111111-1111-1111-1111-111111111111', 'Fake Music', 'music', 'mock://music', 200000, 0, 10, 'active', '[]', '["wav"]', 'fake', 60),
  ('11111111-1111-1111-1111-111111111111', 'Fake QA', 'qa', 'mock://qa', 100000, 0, 10, 'active', '[]', '["text"]', 'fake', 80),
  ('11111111-1111-1111-1111-111111111111', 'Fake SEO', 'seo', 'mock://seo', 100000, 0, 10, 'active', '["fr","en"]', '["text"]', 'fake', 70),
  ('11111111-1111-1111-1111-111111111111', 'Fake Licensing', 'licensing', 'mock://licensing', 100000, 0, 10, 'active', '[]', '["text"]', 'fake', 80);

insert into storage_backends (workspace_id, name, kind, config_encrypted, priority, status, region) values
  ('11111111-1111-1111-1111-111111111111', 'Local Storage', 'local', '', 10, 'active', 'local');
