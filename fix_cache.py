import json

with open('cache_map.json', 'r') as f:
    data = json.load(f)

data['4'] = "SELECT DATE(start_time) as date, COUNT(DISTINCT customer_id) as dau FROM sessions WHERE country = 'GB' GROUP BY DATE(start_time) ORDER BY date;"
data['12'] = "SELECT CASE WHEN country = 'GB' THEN 'UK' ELSE country END as country, COUNT(order_id) as total_orders FROM orders WHERE country IN ('US', 'GB') GROUP BY country;"

with open('cache_map.json', 'w') as f:
    json.dump(data, f)
