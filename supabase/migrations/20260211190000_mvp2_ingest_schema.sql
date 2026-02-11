
-- Create the "entities" table
CREATE TABLE public.entities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text UNIQUE NOT NULL,
    name text NOT NULL,
    entity_type text NOT NULL CHECK (entity_type IN ('destination', 'hotel', 'poi', 'other')),
    destination_id uuid REFERENCES public.destinations(id) ON DELETE SET NULL,
    priority text NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
    refresh_cadence_days int NOT NULL DEFAULT 30 CHECK (refresh_cadence_days IN (7, 14, 30, 60, 90, 180)),
    next_refresh_at timestamptz NULL,
    last_attempt_at timestamptz NULL,
    last_success_at timestamptz NULL,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused')),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    created_by uuid REFERENCES auth.users(id),
    updated_by uuid REFERENCES auth.users(id)
);

-- Indexes for "entities"
CREATE INDEX idx_entities_destination_id ON public.entities (destination_id);
CREATE INDEX idx_entities_next_refresh_at ON public.entities (next_refresh_at);
CREATE INDEX idx_entities_status_priority ON public.entities (status, priority);

-- Create the "entity_sources" table
CREATE TABLE public.entity_sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL REFERENCES public.entities(id) ON DELETE CASCADE,
    source_type text NOT NULL CHECK (source_type IN ('primary', 'fallback')),
    url text NOT NULL,
    allowed boolean NOT NULL DEFAULT true,
    created_at timestamptz DEFAULT now(),
    created_by uuid REFERENCES auth.users(id),
    UNIQUE (entity_id, source_type)
);

-- Index for "entity_sources"
CREATE INDEX idx_entity_sources_entity_id ON public.entity_sources (entity_id);

-- Create the "ingest_jobs" table
CREATE TABLE public.ingest_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL REFERENCES public.entities(id) ON DELETE CASCADE,
    reason text NOT NULL CHECK (reason IN ('new_entity', 'refresh', 'manual')),
    status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    locked_at timestamptz NULL,
    locked_by text NULL,
    attempts int NOT NULL DEFAULT 0,
    error text NULL,
    scheduled_for timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Indexes for "ingest_jobs"
CREATE INDEX idx_ingest_jobs_status_scheduled_for ON public.ingest_jobs (status, scheduled_for);
CREATE INDEX idx_ingest_jobs_entity_id ON public.ingest_jobs (entity_id);

-- Create the "facts_snapshots" table
CREATE TABLE public.facts_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL REFERENCES public.entities(id) ON DELETE CASCADE,
    extractor text NOT NULL, -- 'openai'|'local'|'other'
    model text NULL,
    facts jsonb NOT NULL,
    evidence jsonb NOT NULL,
    meta jsonb NOT NULL,
    score numeric NULL,
    label text NULL,
    created_at timestamptz DEFAULT now()
);

-- Index for "facts_snapshots"
CREATE INDEX idx_facts_snapshots_entity_id_created_at ON public.facts_snapshots (entity_id, created_at);

-- Create the "facts_current" table
CREATE TABLE public.facts_current (
    entity_id uuid PRIMARY KEY REFERENCES public.entities(id) ON DELETE CASCADE,
    snapshot_id uuid NOT NULL REFERENCES public.facts_snapshots(id) ON DELETE RESTRICT,
    updated_at timestamptz DEFAULT now(),
    updated_by uuid REFERENCES auth.users(id)
);

-- Index for "facts_current"
CREATE INDEX idx_facts_current_snapshot_id ON public.facts_current (snapshot_id);

-- Create the "facts_proposed" table
CREATE TABLE public.facts_proposed (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL REFERENCES public.entities(id) ON DELETE CASCADE,
    snapshot_id uuid NOT NULL REFERENCES public.facts_snapshots(id) ON DELETE RESTRICT,
    diff jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending_review' CHECK (status IN ('pending_review', 'accepted', 'rejected')),
    created_at timestamptz DEFAULT now(),
    reviewed_at timestamptz NULL,
    reviewed_by uuid REFERENCES auth.users(id),
    review_note text NULL
);

-- Indexes for "facts_proposed"
CREATE INDEX idx_facts_proposed_status_created_at ON public.facts_proposed (status, created_at);
CREATE INDEX idx_facts_proposed_entity_id ON public.facts_proposed (entity_id);

-- Create the "review_actions" table
CREATE TABLE public.review_actions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    proposed_id uuid NOT NULL REFERENCES public.facts_proposed(id) ON DELETE CASCADE,
    action text NOT NULL CHECK (action IN ('accept', 'reject')),
    user_id uuid REFERENCES auth.users(id),
    note text NULL,
    created_at timestamptz DEFAULT now()
);

-- Index for "review_actions"
CREATE INDEX idx_review_actions_proposed_id ON public.review_actions (proposed_id);


-- RLS and Policies (Admin + Service Role)

-- Enable RLS for all new tables
ALTER TABLE public.entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entity_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingest_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.facts_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.facts_current ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.facts_proposed ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_actions ENABLE ROW LEVEL SECURITY;

-- Policies for "admin" role
CREATE POLICY "Admins can manage entities"
ON public.entities
FOR ALL
USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()));

CREATE POLICY "Admins can manage entity_sources"
ON public.entity_sources
FOR ALL
USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()));

CREATE POLICY "Admins can manage ingest_jobs"
ON public.ingest_jobs
FOR ALL
USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()));

CREATE POLICY "Admins can manage facts_snapshots"
ON public.facts_snapshots
FOR ALL
USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()));

CREATE POLICY "Admins can manage facts_current"
ON public.facts_current
FOR ALL
USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()));

CREATE POLICY "Admins can manage facts_proposed"
ON public.facts_proposed
FOR ALL
USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()));

CREATE POLICY "Admins can manage review_actions"
ON public.review_actions
FOR ALL
USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()));

-- Policies for "service_role"
CREATE POLICY "Service role can manage entities"
ON public.entities
FOR ALL
USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage entity_sources"
ON public.entity_sources
FOR ALL
USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage ingest_jobs"
ON public.ingest_jobs
FOR ALL
USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage facts_snapshots"
ON public.facts_snapshots
FOR ALL
USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage facts_current"
ON public.facts_current
FOR ALL
USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage facts_proposed"
ON public.facts_proposed
FOR ALL
USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage review_actions"
ON public.review_actions
FOR ALL
USING (auth.role() = 'service_role');

-- Specific Policies
CREATE POLICY "Service role can insert facts_snapshots"
ON public.facts_snapshots
FOR INSERT
WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Admin and service role can select facts_snapshots"
ON public.facts_snapshots
FOR SELECT
USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()) OR auth.role() = 'service_role');

CREATE POLICY "Service role can update ingest_jobs"
ON public.ingest_jobs
FOR UPDATE
USING (auth.role() = 'service_role');

CREATE POLICY "Admins can select ingest_jobs"
ON public.ingest_jobs
FOR SELECT
USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()));

CREATE POLICY "Admins can insert manual ingest_jobs"
ON public.ingest_jobs
FOR INSERT
WITH CHECK (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()) AND reason = 'manual');


-- Audit Triggers (valikoidusti)
-- Assumes a function named log_audit_trail() exists

CREATE TRIGGER entities_audit_trail
BEFORE INSERT OR UPDATE OR DELETE ON public.entities
FOR EACH ROW EXECUTE FUNCTION public.log_audit_trail();

CREATE TRIGGER facts_current_audit_trail
BEFORE INSERT OR UPDATE OR DELETE ON public.facts_current
FOR EACH ROW EXECUTE FUNCTION public.log_audit_trail();

CREATE TRIGGER facts_proposed_audit_trail
BEFORE INSERT OR UPDATE OR DELETE ON public.facts_proposed
FOR EACH ROW EXECUTE FUNCTION public.log_audit_trail();
