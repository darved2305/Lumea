-- Seed script for generic_catalog table
-- Run this directly in your Neon SQL console or via psql

-- First, create the table if it doesn't exist
CREATE TABLE IF NOT EXISTS generic_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    salts TEXT[] NOT NULL,
    strength VARCHAR(50),
    dosage_form VARCHAR(50),
    release_type VARCHAR(20),
    manufacturer VARCHAR(255),
    price_mrp DECIMAL(10,2),
    pack_size VARCHAR(50),
    is_jan_aushadhi BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for faster salt-based searches
CREATE INDEX IF NOT EXISTS idx_generic_catalog_salts ON generic_catalog USING GIN(salts);
CREATE INDEX IF NOT EXISTS idx_generic_catalog_brand ON generic_catalog(brand_name);
CREATE INDEX IF NOT EXISTS idx_generic_catalog_jan ON generic_catalog(is_jan_aushadhi);

-- Clear existing data (optional - remove if you want to keep existing data)
TRUNCATE TABLE generic_catalog;

-- Insert Jan Aushadhi medicines (cheaper alternatives)
INSERT INTO generic_catalog (brand_name, generic_name, salts, strength, dosage_form, release_type, manufacturer, price_mrp, pack_size, is_jan_aushadhi) VALUES
-- Paracetamol
('Paracetamol', 'Paracetamol', ARRAY['Paracetamol'], '500mg', 'Tablet', NULL, 'Jan Aushadhi', 5.00, '10 tablets', TRUE),
('Paracetamol', 'Paracetamol', ARRAY['Paracetamol'], '650mg', 'Tablet', NULL, 'Jan Aushadhi', 6.50, '10 tablets', TRUE),
('Paracetamol Suspension', 'Paracetamol', ARRAY['Paracetamol'], '125mg/5ml', 'Suspension', NULL, 'Jan Aushadhi', 15.00, '60ml', TRUE),

-- Metformin
('Metformin', 'Metformin', ARRAY['Metformin'], '500mg', 'Tablet', NULL, 'Jan Aushadhi', 12.00, '20 tablets', TRUE),
('Metformin', 'Metformin', ARRAY['Metformin'], '850mg', 'Tablet', NULL, 'Jan Aushadhi', 18.00, '20 tablets', TRUE),
('Metformin SR', 'Metformin', ARRAY['Metformin'], '500mg', 'Tablet', 'SR', 'Jan Aushadhi', 15.00, '15 tablets', TRUE),

-- Atorvastatin
('Atorvastatin', 'Atorvastatin', ARRAY['Atorvastatin'], '10mg', 'Tablet', NULL, 'Jan Aushadhi', 25.00, '10 tablets', TRUE),
('Atorvastatin', 'Atorvastatin', ARRAY['Atorvastatin'], '20mg', 'Tablet', NULL, 'Jan Aushadhi', 45.00, '10 tablets', TRUE),
('Atorvastatin', 'Atorvastatin', ARRAY['Atorvastatin'], '40mg', 'Tablet', NULL, 'Jan Aushadhi', 80.00, '10 tablets', TRUE),

-- Amlodipine
('Amlodipine', 'Amlodipine', ARRAY['Amlodipine'], '5mg', 'Tablet', NULL, 'Jan Aushadhi', 8.00, '10 tablets', TRUE),
('Amlodipine', 'Amlodipine', ARRAY['Amlodipine'], '10mg', 'Tablet', NULL, 'Jan Aushadhi', 15.00, '10 tablets', TRUE),

-- Aspirin
('Aspirin', 'Aspirin', ARRAY['Aspirin'], '75mg', 'Tablet', NULL, 'Jan Aushadhi', 4.00, '10 tablets', TRUE),
('Aspirin', 'Aspirin', ARRAY['Aspirin'], '150mg', 'Tablet', NULL, 'Jan Aushadhi', 6.00, '10 tablets', TRUE),

-- Pantoprazole
('Pantoprazole', 'Pantoprazole', ARRAY['Pantoprazole'], '40mg', 'Tablet', NULL, 'Jan Aushadhi', 18.00, '15 tablets', TRUE),

-- Omeprazole
('Omeprazole', 'Omeprazole', ARRAY['Omeprazole'], '20mg', 'Capsule', NULL, 'Jan Aushadhi', 12.00, '10 capsules', TRUE),

-- Losartan
('Losartan', 'Losartan', ARRAY['Losartan'], '50mg', 'Tablet', NULL, 'Jan Aushadhi', 22.00, '10 tablets', TRUE),
('Losartan', 'Losartan', ARRAY['Losartan'], '25mg', 'Tablet', NULL, 'Jan Aushadhi', 15.00, '10 tablets', TRUE),

-- Clopidogrel
('Clopidogrel', 'Clopidogrel', ARRAY['Clopidogrel'], '75mg', 'Tablet', NULL, 'Jan Aushadhi', 30.00, '10 tablets', TRUE);

-- Insert branded alternatives (for comparison)
INSERT INTO generic_catalog (brand_name, generic_name, salts, strength, dosage_form, release_type, manufacturer, price_mrp, pack_size, is_jan_aushadhi) VALUES
-- Paracetamol brands
('Crocin', 'Paracetamol', ARRAY['Paracetamol'], '500mg', 'Tablet', NULL, 'GSK', 35.00, '15 tablets', FALSE),
('Dolo 650', 'Paracetamol', ARRAY['Paracetamol'], '650mg', 'Tablet', NULL, 'Micro Labs', 30.00, '15 tablets', FALSE),

-- Metformin brands
('Glycomet', 'Metformin', ARRAY['Metformin'], '500mg', 'Tablet', NULL, 'USV Ltd', 85.00, '20 tablets', FALSE),
('Glycomet SR', 'Metformin', ARRAY['Metformin'], '500mg', 'Tablet', 'SR', 'USV Ltd', 105.00, '15 tablets', FALSE),

-- Atorvastatin brands
('Atorva', 'Atorvastatin', ARRAY['Atorvastatin'], '10mg', 'Tablet', NULL, 'Zydus Cadila', 120.00, '10 tablets', FALSE),
('Lipitor', 'Atorvastatin', ARRAY['Atorvastatin'], '20mg', 'Tablet', NULL, 'Pfizer', 350.00, '10 tablets', FALSE);

-- Verify insertion
SELECT 
    COUNT(*) as total_medicines,
    SUM(CASE WHEN is_jan_aushadhi THEN 1 ELSE 0 END) as jan_aushadhi_count,
    SUM(CASE WHEN NOT is_jan_aushadhi THEN 1 ELSE 0 END) as branded_count,
    AVG(price_mrp) FILTER (WHERE is_jan_aushadhi) as avg_jan_aushadhi_price,
    AVG(price_mrp) FILTER (WHERE NOT is_jan_aushadhi) as avg_branded_price
FROM generic_catalog;

-- Sample query to test substitute matching
SELECT 
    brand_name, 
    salts, 
    strength, 
    dosage_form, 
    release_type,
    price_mrp,
    is_jan_aushadhi
FROM generic_catalog
WHERE 'Paracetamol' = ANY(salts)
ORDER BY is_jan_aushadhi DESC, price_mrp ASC
LIMIT 5;
