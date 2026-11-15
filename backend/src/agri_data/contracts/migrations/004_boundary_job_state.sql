ALTER TABLE boundary_imports DROP CONSTRAINT boundary_imports_status_check;
ALTER TABLE boundary_imports ADD CONSTRAINT boundary_imports_status_check
    CHECK (status IN ('in_progress','complete','partial','failed'));
ALTER TABLE boundary_imports ALTER COLUMN completed_at DROP NOT NULL;
