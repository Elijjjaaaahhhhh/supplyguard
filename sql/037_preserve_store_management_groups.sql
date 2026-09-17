-- A store can carry products from multiple management groups on the same day.
-- Preserve the observed association rather than choosing an arbitrary group.
CREATE TABLE IF NOT EXISTS core.bridge_store_management_group (
    store_id BIGINT NOT NULL REFERENCES core.dim_store(store_id),
    management_group_id BIGINT NOT NULL,
    PRIMARY KEY (store_id,management_group_id)
);
TRUNCATE core.bridge_store_management_group;
INSERT INTO core.bridge_store_management_group(store_id,management_group_id)
SELECT DISTINCT store_id,management_group_id FROM staging.retail_daily;
