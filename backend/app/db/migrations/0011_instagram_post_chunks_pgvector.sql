-- 0011: Instagram post chunks with pgvector embeddings, for grounded explanations.
--
-- Stage 3 splits every scraped post into chunks (caption, hashtags, comments)
-- and stores each with a 384-number all-MiniLM-L6-v2 embedding here, in the
-- same Postgres database as everything else. The Explain button searches these
-- with match_instagram_chunks() and gives the closest chunks to the LLM as the
-- only evidence it may cite.
--
-- Re-runnable: every statement checks before it creates.

create extension if not exists vector;

create table if not exists public.instagram_post_chunks (
    id              text primary key,
    project_id      text not null references public.projects (id) on delete cascade,
    post_id         text references public.instagram_posts (id) on delete cascade,
    source_id       text,
    role            text,
    competitor_id   text,
    field_type      text not null default '',
    chunk_index     integer not null default 0,
    chunk_text      text not null,
    post_url        text not null default '',
    embedding       vector(384),
    created_at      timestamptz not null default now()
);

create index if not exists instagram_post_chunks_project_idx
    on public.instagram_post_chunks (project_id, role, competitor_id);

create index if not exists instagram_post_chunks_embedding_idx
    on public.instagram_post_chunks using hnsw (embedding vector_cosine_ops);

alter table public.instagram_post_chunks enable row level security;

drop policy if exists instagram_post_chunks_owner_all on public.instagram_post_chunks;
create policy instagram_post_chunks_owner_all on public.instagram_post_chunks
    for all using (exists (
        select 1 from public.projects p
        where p.id = instagram_post_chunks.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = instagram_post_chunks.project_id and p.owner_id = auth.uid()));

-- Semantic search inside one project, optionally one side (own / competitor).
-- security invoker: the caller's row-level security still applies.
create or replace function public.match_instagram_chunks(
    p_project_id    text,
    p_query         vector(384),
    p_role          text default null,
    p_competitor_id text default null,
    p_count         integer default 4
)
returns table (
    id            text,
    post_id       text,
    source_id     text,
    role          text,
    competitor_id text,
    field_type    text,
    chunk_index   integer,
    chunk_text    text,
    post_url      text,
    similarity    double precision
)
language sql stable security invoker
set search_path = public
as $$
    select c.id, c.post_id, c.source_id, c.role, c.competitor_id, c.field_type,
           c.chunk_index, c.chunk_text, c.post_url,
           1 - (c.embedding <=> p_query) as similarity
    from public.instagram_post_chunks c
    where c.project_id = p_project_id
      and c.embedding is not null
      and (p_role is null or c.role = p_role)
      and (p_competitor_id is null or c.competitor_id = p_competitor_id)
    order by c.embedding <=> p_query
    limit greatest(p_count, 1);
$$;

grant execute on function public.match_instagram_chunks(text, vector, text, text, integer)
    to authenticated, service_role;
