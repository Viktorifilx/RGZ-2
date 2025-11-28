INSERT INTO tmp_assign (ad_id, master_id)
SELECT
    a.id,
    (
        SELECT u.id
        FROM users u
        WHERE u.role = 'master'
        ORDER BY u.id
        LIMIT 1 OFFSET ((row_number - 1) % (SELECT COUNT(*) FROM users WHERE role='master'))
    ) AS master_id
FROM (
    SELECT id,
           ROW_NUMBER() OVER (ORDER BY id) AS row_number
    FROM ads
) a;
