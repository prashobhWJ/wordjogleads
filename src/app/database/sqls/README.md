# Database SQL Scripts

This folder contains SQL scripts for managing the leads table and sample data.

## Scripts

### 01_create_leads_table.sql
Creates the `leads` table with all necessary columns, indexes, triggers, and constraints.

**Features:**
- Comprehensive lead information storage
- Automatic timestamp management (created_at, updated_at)
- Indexes for common query patterns
- Database comments for documentation

**To run:**
```bash
psql -U your_user -d your_database -f 01_create_leads_table.sql
```

### 02_insert_sample_leads.sql
Inserts sample lead records for testing and development.

**Contains:**
- Ryan Beuglet (the original lead from requirements)
- 4 additional sample leads with varied data

**To run:**
```bash
psql -U your_user -d your_database -f 02_insert_sample_leads.sql
```

### 03_drop_leads_table.sql
Drops the leads table and all related objects (triggers, functions, indexes).

**⚠️ WARNING:** This will delete all data in the leads table. Use only for development/testing.

**To run:**
```bash
psql -U your_user -d your_database -f 03_drop_leads_table.sql
```

## Table Structure

The `leads` table includes:

### Personal Information
- `lead_id` - Unique lead identifier
- `first_name`, `last_name`, `full_name`
- `email`, `phone`
- `date_of_birth`

### Address Information
- `address_line1`, `address_line2`
- `city`, `state_province`
- `postal_code`
- `country`, `country_code`

### Vehicle & Financial
- `vehicle_type` - Type of vehicle
- `current_credit` - Credit status/type

### Employment
- `employment_status`
- `job_title`, `company_name`
- `monthly_salary_min`, `monthly_salary_max`
- `employment_length`, `length_at_company`

### Residency
- `length_at_home_address`

### Metadata
- `created_at` - Auto-set on insert
- `updated_at` - Auto-updated on modification

## Usage Examples

### Create table and insert sample data:
```bash
psql -U your_user -d your_database -f 01_create_leads_table.sql
psql -U your_user -d your_database -f 02_insert_sample_leads.sql
```

### Query examples:
```sql
-- Get all leads
SELECT * FROM leads;

-- Find lead by ID
SELECT * FROM leads WHERE lead_id = 'HIWCOSE3';

-- Find self-employed leads
SELECT * FROM leads WHERE employment_status = 'Self-Employed';

-- Find leads by vehicle type
SELECT * FROM leads WHERE vehicle_type = 'Truck';

-- Find leads by salary range
SELECT * FROM leads 
WHERE monthly_salary_min >= 3000 
  AND monthly_salary_max <= 5000;
```

## Notes

- All timestamps are automatically managed
- The `lead_id` field has a UNIQUE constraint
- Indexes are created for common query patterns
- The table uses SERIAL for auto-incrementing primary key
