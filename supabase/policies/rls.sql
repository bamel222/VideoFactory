-- RLS policies per workspace, role and action
alter table users enable row level security;
alter table workspaces enable row level security;
alter table providers enable row level security;
alter table storage_backends enable row level security;
alter table series enable row level security;
alter table episodes enable row level security;
alter table scenes enable row level security;
alter table segments enable row level security;
alter table job_runs enable row level security;
alter table job_tasks enable row level security;
alter table checkpoints enable row level security;
alter table continuity_packs enable row level security;
alter table budget_forecasts enable row level security;
alter table dry_runs enable row level security;
alter table assets enable row level security;
alter table licence_records enable row level security;
alter table review_records enable row level security;
alter table seo_packages enable row level security;
alter table shorts_packages enable row level security;
alter table ab_test_variants enable row level security;
alter table audit_logs enable row level security;

-- Helper: current user's workspace id (set via JWT custom claim)
create or replace function public.current_workspace_id() returns uuid
language sql stable as $$
  select coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'workspace_id')::uuid, '00000000-0000-0000-0000-000000000000'::uuid)
$$;

-- Helper: current user's role
create or replace function public.current_role() returns text
language sql stable as $$
  select coalesce(current_setting('request.jwt.claims', true)::jsonb ->> 'role', 'anon')
$$;

-- Workspaces: member can read own workspace
create policy workspace_select on workspaces for select
  using (id = public.current_workspace_id());
create policy workspace_update_owner on workspaces for update
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid());

-- Users: same-workspace select; owner manages
create policy users_select_same_ws on users for select
  using (workspace_id = public.current_workspace_id());
create policy users_manage_owner on users for all
  using (public.current_role() = 'owner' and workspace_id = public.current_workspace_id());

-- Providers: owner full, admin non-critical ops, reviewer read-only
create policy providers_read_ws on providers for select
  using (workspace_id = public.current_workspace_id());
create policy providers_write_owner_admin on providers for insert
  with check (public.current_role() in ('owner','admin') and workspace_id = public.current_workspace_id());
create policy providers_update_owner on providers for update
  using (public.current_role() = 'owner' and workspace_id = public.current_workspace_id());
create policy providers_update_admin on providers for update
  using (public.current_role() = 'admin' and workspace_id = public.current_workspace_id());
create policy providers_delete_owner on providers for delete
  using (public.current_role() = 'owner' and workspace_id = public.current_workspace_id());

-- Storage: owner + admin
create policy storage_read_ws on storage_backends for select
  using (workspace_id = public.current_workspace_id());
create policy storage_write_admin on storage_backends for all
  using (public.current_role() in ('owner','admin') and workspace_id = public.current_workspace_id());

-- Series / episodes / scenes / segments: reviewer read, owner/admin write
create policy series_read_ws on series for select
  using (workspace_id = public.current_workspace_id());
create policy series_write_ws on series for all
  using (public.current_role() in ('owner','admin') and workspace_id = public.current_workspace_id());

create policy episodes_read_ws on episodes for select
  using (series_id in (select id from series where workspace_id = public.current_workspace_id()));
create policy episodes_write_ws on episodes for all
  using (public.current_role() in ('owner','admin') and series_id in (select id from series where workspace_id = public.current_workspace_id()));

-- Review records: reviewer can read + comment, admin/owner decide
create policy review_read_ws on review_records for select
  using (episode_id in (select id from episodes where series_id in (select id from series where workspace_id = public.current_workspace_id())));
create policy review_comment_reviewer on review_records for insert
  with check (public.current_role() in ('reviewer','admin','owner'));
create policy review_decide_admin on review_records for update
  using (public.current_role() in ('admin','owner'));

-- Audit: owner/admin read
create policy audit_read_admin on audit_logs for select
  using (public.current_role() in ('owner','admin'));
create policy audit_write_system on audit_logs for insert
  with check (true);
