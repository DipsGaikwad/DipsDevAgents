-- CKD agent integration migration. Run once against the existing ckd_project database.
-- Does not alter existing patient, visit, lab, or user rows.
CREATE TABLE IF NOT EXISTS patient_analyses (
  analysis_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  patient_id VARCHAR(20) NOT NULL,
  risk_level VARCHAR(30) NOT NULL DEFAULT 'UNASSESSED',
  probability DECIMAL(8,6) NULL,
  model_used VARCHAR(120) NULL,
  egfr_trend VARCHAR(80) NULL,
  egfr_slope DECIMAL(9,3) NULL,
  latest_egfr DECIMAL(8,2) NULL,
  priority VARCHAR(40) NULL,
  priority_score INT NULL,
  result_json JSON NULL,
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (analysis_id),
  KEY ix_patient_analyses_patient_id (patient_id),
  CONSTRAINT fk_patient_analyses_patient FOREIGN KEY (patient_id)
    REFERENCES patients(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
