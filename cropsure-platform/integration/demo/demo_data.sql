-- =============================================================
-- CropSure AI - Demo Data
-- Pre-populated with 5 realistic Kenyan farms near Nyeri
-- =============================================================

TRUNCATE TABLE payouts, ndvi_readings, farms, farmers CASCADE;

INSERT INTO farmers (id, full_name, phone, mpesa_phone, village, enrollment_channel, created_at) VALUES
('f001', 'Wanjiku Kamau', '+254712345678', '0712345678', 'Karatina', 'whatsapp', NOW() - INTERVAL '90 days'),
('f002', 'Mwangi Njoroge', '+254723456789', '0723456789', 'Othaya', 'ussd', NOW() - INTERVAL '85 days'),
('f003', 'Achieng Otieno', '+254734567890', '0734567890', 'Nyeri Town', 'agent', NOW() - INTERVAL '80 days'),
('f004', 'Kipchoge Mutai', '+254745678901', '0745678901', 'Mukurweini', 'whatsapp', NOW() - INTERVAL '75 days'),
('f005', 'Zawadi Muthoni', '+254756789012', '0756789012', 'Tetu', 'ussd', NOW() - INTERVAL '70 days');

INSERT INTO farms (id, farmer_id, polygon, acres, crop, farming_type, risk_zone, premium, policy_number, status, planting_date, created_at) VALUES
('farm001', 'f001', ST_GeomFromText('POLYGON((36.9821 -0.4182, 36.9841 -0.4182, 36.9841 -0.4202, 36.9821 -0.4202, 36.9821 -0.4182))', 4326), 2.5, 'maize', 'monocrop', 'medium', 900, 'CS-2026-001', 'active', NOW() - INTERVAL '85 days', NOW() - INTERVAL '90 days'),
('farm002', 'f002', ST_GeomFromText('POLYGON((36.9650 -0.3950, 36.9670 -0.3950, 36.9670 -0.3970, 36.9650 -0.3970, 36.9650 -0.3950))', 4326), 3.0, 'beans', 'intercrop', 'medium', 900, 'CS-2026-002', 'active', NOW() - INTERVAL '80 days', NOW() - INTERVAL '85 days'),
('farm003', 'f003', ST_GeomFromText('POLYGON((36.9479 -0.4167, 36.9499 -0.4167, 36.9499 -0.4187, 36.9479 -0.4187, 36.9479 -0.4167))', 4326), 1.5, 'maize', 'monocrop', 'low', 360, 'CS-2026-003', 'active', NOW() - INTERVAL '75 days', NOW() - INTERVAL '80 days'),
('farm004', 'f004', ST_GeomFromText('POLYGON((37.0123 -0.5234, 37.0143 -0.5234, 37.0143 -0.5254, 37.0123 -0.5254, 37.0123 -0.5234))', 4326), 4.0, 'tea', 'monocrop', 'low', 1440, 'CS-2026-004', 'stress_detected', NOW() - INTERVAL '70 days', NOW() - INTERVAL '75 days'),
('farm005', 'f005', ST_GeomFromText('POLYGON((36.9234 -0.3456, 36.9254 -0.3456, 36.9254 -0.3476, 36.9234 -0.3476, 36.9234 -0.3456))', 4326), 2.0, 'maize', 'intercrop', 'high', 1080, 'CS-2026-005', 'payout_sent', NOW() - INTERVAL '65 days', NOW() - INTERVAL '70 days');

INSERT INTO ndvi_readings (farm_id, ndvi_value, baseline_value, deviation_percent, stress_detected, reading_date) VALUES
('farm001', 0.21, 0.20, 5.0, false, NOW() - INTERVAL '85 days'),
('farm001', 0.52, 0.51, 1.9, false, NOW() - INTERVAL '75 days'),
('farm001', 0.71, 0.70, 1.4, false, NOW() - INTERVAL '65 days'),
('farm001', 0.74, 0.73, 1.4, false, NOW() - INTERVAL '55 days'),
('farm001', 0.69, 0.70, -1.4, false, NOW() - INTERVAL '45 days'),
('farm001', 0.73, 0.72, 1.4, false, NOW() - INTERVAL '5 days'),
('farm002', 0.19, 0.20, -5.0, false, NOW() - INTERVAL '80 days'),
('farm002', 0.48, 0.49, -2.0, false, NOW() - INTERVAL '70 days'),
('farm002', 0.63, 0.62, 1.6, false, NOW() - INTERVAL '60 days'),
('farm002', 0.61, 0.61, 0.0, false, NOW() - INTERVAL '5 days'),
('farm003', 0.22, 0.21, 4.8, false, NOW() - INTERVAL '75 days'),
('farm003', 0.58, 0.57, 1.8, false, NOW() - INTERVAL '65 days'),
('farm003', 0.74, 0.73, 1.4, false, NOW() - INTERVAL '55 days'),
('farm003', 0.74, 0.74, 0.0, false, NOW() - INTERVAL '5 days'),
('farm004', 0.73, 0.72, 1.4, false, NOW() - INTERVAL '65 days'),
('farm004', 0.74, 0.73, 1.4, false, NOW() - INTERVAL '60 days'),
('farm004', 0.61, 0.73, -16.4, false, NOW() - INTERVAL '45 days'),
('farm004', 0.52, 0.73, -28.8, true, NOW() - INTERVAL '40 days'),
('farm004', 0.46, 0.73, -37.0, true, NOW() - INTERVAL '25 days'),
('farm004', 0.42, 0.73, -42.5, true, NOW() - INTERVAL '5 days'),
('farm005', 0.20, 0.21, -4.8, false, NOW() - INTERVAL '65 days'),
('farm005', 0.55, 0.57, -3.5, false, NOW() - INTERVAL '55 days'),
('farm005', 0.43, 0.68, -36.8, true, NOW() - INTERVAL '40 days'),
('farm005', 0.38, 0.68, -44.1, true, NOW() - INTERVAL '35 days'),
('farm005', 0.72, 0.69, 4.3, false, NOW() - INTERVAL '5 days');

INSERT INTO payouts (farm_id, farmer_id, amount, reason, stress_type, ndvi_drop_percent, policy_number, mpesa_transaction_id, status, triggered_at, paid_at) VALUES
('farm005', 'f005', 4200, 'Vegetation health dropped 44% below your June baseline. Drought stress confirmed.', 'drought', 44.1, 'CS-2026-005', 'MPX1234567', 'completed', NOW() - INTERVAL '35 days', NOW() - INTERVAL '35 days' + INTERVAL '2 hours');
