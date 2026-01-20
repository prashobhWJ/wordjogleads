-- Create Leads Table
-- This table captures lead information including personal details, contact information,
-- vehicle and financial information, employment details, and residency information

CREATE TABLE IF NOT EXISTS leads (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Lead Identification
    lead_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Personal Information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(200),
    email VARCHAR(255),
    phone VARCHAR(50),
    date_of_birth DATE,
    
    -- Address Information
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    country_code VARCHAR(10),  -- e.g., "ON" for Ontario
    
    -- Vehicle Information
    vehicle_type VARCHAR(50),  -- e.g., "Truck", "Car", "SUV"
    
    -- Financial Information
    current_credit VARCHAR(100),  -- e.g., "Self-employed salary"
    
    -- Employment Information
    employment_status VARCHAR(50),  -- e.g., "Self-Employed", "Employed", "Unemployed"
    job_title VARCHAR(100),
    company_name VARCHAR(200),
    monthly_salary_min DECIMAL(10, 2),  -- Minimum monthly salary range
    monthly_salary_max DECIMAL(10, 2),  -- Maximum monthly salary range
    employment_length VARCHAR(50),  -- e.g., "2 years+", "1-2 years"
    length_at_company VARCHAR(50),  -- e.g., "2 years", "1 year"
    
    -- Residency Information
    length_at_home_address VARCHAR(50),  -- e.g., "2 years+", "1-2 years"
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for common queries
    CONSTRAINT leads_lead_id_key UNIQUE (lead_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_leads_lead_id ON leads(lead_id);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_employment_status ON leads(employment_status);
CREATE INDEX IF NOT EXISTS idx_leads_vehicle_type ON leads(vehicle_type);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments to table and columns for documentation
COMMENT ON TABLE leads IS 'Stores lead information including personal, contact, vehicle, financial, employment, and residency details';
COMMENT ON COLUMN leads.lead_id IS 'Unique lead identifier (e.g., HIWCOSE3)';
COMMENT ON COLUMN leads.full_name IS 'Full name of the lead';
COMMENT ON COLUMN leads.email IS 'Email address of the lead';
COMMENT ON COLUMN leads.phone IS 'Phone number of the lead';
COMMENT ON COLUMN leads.date_of_birth IS 'Date of birth of the lead';
COMMENT ON COLUMN leads.vehicle_type IS 'Type of vehicle (Truck, Car, SUV, etc.)';
COMMENT ON COLUMN leads.current_credit IS 'Current credit status or type';
COMMENT ON COLUMN leads.employment_status IS 'Current employment status';
COMMENT ON COLUMN leads.monthly_salary_min IS 'Minimum monthly salary in the range';
COMMENT ON COLUMN leads.monthly_salary_max IS 'Maximum monthly salary in the range';
COMMENT ON COLUMN leads.length_at_home_address IS 'Length of time at current home address';
