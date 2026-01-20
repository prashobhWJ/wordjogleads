-- Drop Leads Table and Related Objects
-- WARNING: This will delete all data in the leads table
-- Use this script only for development/testing or when you need to recreate the table

-- Drop the trigger first
DROP TRIGGER IF EXISTS update_leads_updated_at ON leads;

-- Drop the function
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop indexes
DROP INDEX IF EXISTS idx_leads_lead_id;
DROP INDEX IF EXISTS idx_leads_email;
DROP INDEX IF EXISTS idx_leads_phone;
DROP INDEX IF EXISTS idx_leads_created_at;
DROP INDEX IF EXISTS idx_leads_employment_status;
DROP INDEX IF EXISTS idx_leads_vehicle_type;

-- Drop the table
DROP TABLE IF EXISTS leads;

-- Verify table is dropped
SELECT 
    table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name = 'leads';
