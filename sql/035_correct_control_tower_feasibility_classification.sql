-- Phase 8 QA: feasibility precedes funding-only escalation.
-- In-place classification correction; allocation amounts/quantities are untouched.
UPDATE mart.control_tower
SET control_tower_status = 'CONSTRAINED - ESCALATE',
    recommended_action = CASE
        WHEN urgency_band IN ('CRITICAL', 'HIGH')
        THEN 'Urgent: resolve procurement/physical constraints; reassess funding'
        ELSE 'Review MOQ, capacity, capital or shelf-life constraint'
    END
WHERE reorder_required AND final_recommended_quantity <= 0
  AND (control_tower_status <> 'CONSTRAINED - ESCALATE'
       OR recommended_action <> CASE
           WHEN urgency_band IN ('CRITICAL', 'HIGH')
           THEN 'Urgent: resolve procurement/physical constraints; reassess funding'
           ELSE 'Review MOQ, capacity, capital or shelf-life constraint' END);
