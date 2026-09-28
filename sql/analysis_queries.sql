-- name: response_rate_by_wave
SELECT i.wave,
       i.invited,
       i.instrument_items,
       COUNT(r.response_id)                                            AS starts,
       SUM(CASE WHEN r.status = 'Complete' THEN 1 ELSE 0 END)          AS completes,
       ROUND(100.0 * SUM(CASE WHEN r.status = 'Complete' THEN 1 ELSE 0 END) / i.invited, 2) AS response_rate_pct,
       ROUND(100.0 * SUM(CASE WHEN r.status = 'Complete' THEN 1 ELSE 0 END) / COUNT(r.response_id), 2) AS completion_rate_pct
FROM invitations i
LEFT JOIN respondents r ON r.wave = i.wave
GROUP BY i.wave, i.invited, i.instrument_items
ORDER BY i.wave;

-- name: dimension_scores
SELECT ra.dimension,
       COUNT(ra.score)                                                 AS n_ratings,
       ROUND(AVG(ra.score), 3)                                         AS mean_score,
       ROUND(100.0 * AVG(CASE WHEN ra.score >= 4 THEN 1.0 ELSE 0 END), 2) AS top2box_pct,
       ROUND(100.0 * AVG(CASE WHEN ra.score <= 2 THEN 1.0 ELSE 0 END), 2) AS bottom2box_pct
FROM ratings ra
JOIN respondents r ON r.response_id = ra.response_id
WHERE r.status = 'Complete' AND ra.score IS NOT NULL
GROUP BY ra.dimension
ORDER BY mean_score;

-- name: dimension_scores_by_wave
SELECT r.wave, ra.dimension,
       ROUND(AVG(ra.score), 3) AS mean_score
FROM ratings ra
JOIN respondents r ON r.response_id = ra.response_id
WHERE r.status = 'Complete' AND ra.score IS NOT NULL
GROUP BY r.wave, ra.dimension
ORDER BY ra.dimension, r.wave;

-- name: nps_by_wave
SELECT wave,
       COUNT(*) AS respondents,
       ROUND(100.0 * AVG(CASE WHEN nps_likelihood >= 9 THEN 1.0 ELSE 0 END)
           - 100.0 * AVG(CASE WHEN nps_likelihood <= 6 THEN 1.0 ELSE 0 END), 1) AS nps,
       ROUND(AVG(overall_satisfaction), 2) AS avg_overall_satisfaction
FROM respondents
WHERE status = 'Complete'
GROUP BY wave;

-- name: satisfaction_by_student_type
SELECT student_type,
       COUNT(*) AS respondents,
       ROUND(AVG(overall_satisfaction), 2) AS avg_overall_satisfaction
FROM respondents
WHERE status = 'Complete'
GROUP BY student_type
ORDER BY avg_overall_satisfaction;

-- name: satisfaction_by_class_standing
SELECT class_standing,
       COUNT(*) AS respondents,
       ROUND(AVG(overall_satisfaction), 2) AS avg_overall_satisfaction
FROM respondents
WHERE status = 'Complete'
GROUP BY class_standing
ORDER BY avg_overall_satisfaction;

-- name: data_quality_by_wave
SELECT r.wave,
       ROUND(100.0 * AVG(r.straightliner_flag), 2) AS straightlining_pct,
       ROUND(AVG(r.duration_minutes), 2)           AS avg_duration_minutes,
       ROUND(100.0 * (SELECT AVG(CASE WHEN ra.score IS NULL THEN 1.0 ELSE 0 END)
                      FROM ratings ra JOIN respondents r2 ON r2.response_id = ra.response_id
                      WHERE r2.wave = r.wave AND r2.status = 'Complete'), 2) AS item_nonresponse_pct
FROM respondents r
WHERE r.status = 'Complete'
GROUP BY r.wave;

-- name: comment_rate_by_wave
SELECT r.wave,
       COUNT(c.response_id) AS comments,
       ROUND(100.0 * COUNT(c.response_id) / COUNT(r.response_id), 2) AS comment_rate_pct
FROM respondents r
LEFT JOIN comments c ON c.response_id = r.response_id
WHERE r.status = 'Complete'
GROUP BY r.wave;
