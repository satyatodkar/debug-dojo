-- Supabase Migration: 20261017140000_add_session_id_to_agent_audit_logs.sql
-- Description: Adds session_id foreign key column to agent_audit_logs table to link
-- audit entries with the corresponding agent_sessions record.

ALTER TABLE public.agent_audit_logs
ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES public.agent_sessions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_agent_audit_logs_session_id
ON public.agent_audit_logs(session_id);

COMMENT ON COLUMN public.agent_audit_logs.session_id IS 'Foreign key reference to agent_sessions.id';
