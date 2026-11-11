-- Run this once in Supabase: Dashboard -> SQL Editor -> New query -> Run

-- 1. Summary history table -------------------------------------------------
create table if not exists public.summaries (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null default auth.uid() references auth.users(id) on delete cascade,
  file_name    text not null,
  page_count   int,
  summary      text not null,
  storage_path text,
  created_at   timestamptz not null default now()
);

create index if not exists summaries_user_created_idx
  on public.summaries (user_id, created_at desc);

-- 2. Row Level Security: users only access their own rows ------------------
alter table public.summaries enable row level security;

create policy "Users read own summaries"
  on public.summaries for select to authenticated
  using (user_id = (select auth.uid()));

create policy "Users insert own summaries"
  on public.summaries for insert to authenticated
  with check (user_id = (select auth.uid()));

create policy "Users delete own summaries"
  on public.summaries for delete to authenticated
  using (user_id = (select auth.uid()));

-- 3. Private storage bucket for original PDFs -------------------------------
insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do nothing;

-- Files live under "<user_id>/<file>.pdf"; users only touch their own folder.
create policy "Users upload own PDFs"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy "Users read own PDFs"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy "Users delete own PDFs"
  on storage.objects for delete to authenticated
  using (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );
