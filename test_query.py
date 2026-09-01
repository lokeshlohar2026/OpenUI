import db
sql = """SELECT fund_name, nature, sub_nature, riskometer, aum_cr, aum_date, portfolio_turnover_ratio FROM mfi360_funds WHERE fund_id = (SELECT fund_id FROM mfi360_funds WHERE fund_name ILIKE '%SBI%' AND (fund_name ILIKE '%Bluechip%' OR fund_name ILIKE '%Large Cap%') ORDER BY aum_cr DESC NULLS LAST LIMIT 1)"""
res = db.execute_safe_sql(sql)
print(res)

sql2 = """SELECT '1. Category Universe' AS name, COUNT(*) AS value FROM mfi360_funds WHERE sub_nature = 'Small Cap Fund' UNION ALL SELECT '2. AUM > 5000 Cr' AS name, COUNT(*) AS value FROM mfi360_funds WHERE sub_nature = 'Small Cap Fund' AND aum_cr > 5000 UNION ALL SELECT '3. Low Turnover (<50%)' AS name, COUNT(*) AS value FROM mfi360_funds WHERE sub_nature = 'Small Cap Fund' AND aum_cr > 5000 AND portfolio_turnover_ratio < 50"""
print(db.execute_safe_sql(sql2))

# test our fixed MetricCard scenario via direct
sql3 = """SELECT fund_name, riskometer FROM mfi360_funds WHERE fund_name ILIKE '%SBI Large Cap%' ORDER BY aum_cr DESC LIMIT 1"""
print(db.execute_safe_sql(sql3))
