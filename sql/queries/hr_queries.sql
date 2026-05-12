-- ─────────────────────────────────────────────────────────────────────────────
-- hr_queries.sql — Named SQL queries used by the HR ML pipeline
-- ─────────────────────────────────────────────────────────────────────────────

-- get_employee_features: full feature set for attrition classifier
-- :name get_employee_features
SELECT
    e.employee_id,
    e.department,
    e.tenure_months,
    e.salary,
    e.satisfaction_score,
    e.attrition,
    e.absenteeism_days,
    e.anomaly_flag,
    e.attrition_probability,
    PERCENT_RANK() OVER (PARTITION BY e.department ORDER BY e.salary) AS salary_percentile
FROM hr_employees e
ORDER BY e.employee_id;


-- get_department_attrition: attrition rate and satisfaction per department
-- :name get_department_attrition
SELECT
    department,
    COUNT(*)                                                    AS total_employees,
    SUM(CASE WHEN attrition = 1 THEN 1 ELSE 0 END)            AS attrited_count,
    ROUND(
        SUM(CASE WHEN attrition = 1 THEN 1.0 ELSE 0.0 END)
        / COUNT(*) * 100, 2
    )                                                           AS attrition_rate,
    ROUND(AVG(satisfaction_score), 2)                          AS avg_satisfaction,
    ROUND(AVG(absenteeism_days), 1)                            AS avg_absenteeism
FROM hr_employees
GROUP BY department
ORDER BY attrition_rate DESC;


-- get_high_risk_employees: employees above attrition risk threshold
-- :name get_high_risk_employees
SELECT
    employee_id,
    department,
    tenure_months,
    salary,
    satisfaction_score,
    attrition_probability
FROM hr_employees
WHERE attrition_probability > 0.65
ORDER BY attrition_probability DESC;


-- get_monthly_hr_aggregates: for HR anomaly detector training
-- :name get_monthly_hr_aggregates
SELECT
    department,
    snapshot_date,
    COUNT(*)                                                         AS headcount,
    SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END)            AS monthly_attritions,
    ROUND(
        SUM(CASE WHEN attrition_flag = 1 THEN 1.0 ELSE 0.0 END)
        / COUNT(*) * 100, 2
    )                                                                AS monthly_attrition_rate,
    ROUND(AVG(satisfaction_score), 2)                                AS avg_satisfaction,
    ROUND(AVG(absenteeism_days), 1)                                  AS avg_absenteeism_rate
FROM hr_monthly_snapshot
GROUP BY department, snapshot_date
ORDER BY snapshot_date ASC;
