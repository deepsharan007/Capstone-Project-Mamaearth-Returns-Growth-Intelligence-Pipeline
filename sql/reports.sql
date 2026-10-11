-- =====================================================================
-- sql/reports.sql  |  Part 1, Task 3  |  Mamaearth Returns Pipeline
-- Run AFTER schema.sql and seed_data.sql, on the raw (uncleaned) data.
-- Revenue per order line = quantity * price * (1 - discount_pct/100.0)
--   * NULL discount is treated as 0%  -> COALESCE(discount_pct, 0)
--   * We divide by 100.0 (not 100): in SQLite INT/INT is integer division,
--     so 30/100 would give 0 and silently ignore every discount.
-- =====================================================================

-- ---------------------------------------------------------------------
-- a) Order totals: count, total revenue, average order value (2 marks)
-- ---------------------------------------------------------------------
-- OUTPUT:
-- total_orders | total_revenue | avg_order_value
-- -------------+---------------+----------------
-- 180          | 99860.20      | 554.78         
-- (1 row)
SELECT COUNT(*) AS total_orders,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_revenue,
       ROUND(AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS avg_order_value
FROM orders o
JOIN products p ON o.product_id = p.product_id;

-- ---------------------------------------------------------------------
-- b) COUNT(*) vs COUNT(column) (2 marks)
-- ---------------------------------------------------------------------
-- COUNT(*) counts every row; COUNT(rating) skips NULLs -> 15 orders not yet rated.
-- OUTPUT:
-- all_orders | rated_orders | unrated_orders
-- -----------+--------------+---------------
-- 180        | 165          | 15            
-- (1 row)
SELECT COUNT(*)                 AS all_orders,
       COUNT(rating)            AS rated_orders,
       COUNT(*) - COUNT(rating) AS unrated_orders
FROM orders;

-- ---------------------------------------------------------------------
-- c) LEFT JOIN with a genuine zero-match row (3 marks)
-- ---------------------------------------------------------------------
-- Query 1 (LEFT JOIN + HAVING) and Query 2 (NOT IN) are independent;
-- both return the same single customer, confirming the LEFT JOIN result.
-- OUTPUT:
-- customer_id | name   | order_count
-- ------------+--------+------------
-- C045        | Vihaan | 0          
-- (1 row)
SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_count
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
HAVING COUNT(o.order_id) = 0;

-- OUTPUT:
-- customer_id | name  
-- ------------+-------
-- C045        | Vihaan
-- (1 row)
SELECT customer_id, name
FROM customers
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders);

-- ---------------------------------------------------------------------
-- d) GROUP BY + HAVING: cities with return rate above 20% (3 marks)
-- ---------------------------------------------------------------------
-- Excluded correctly: Mumbai 17.9%, Delhi 17.4%.
-- OUTPUT:
-- city      | total_orders | returned_orders | return_rate_pct
-- ----------+--------------+-----------------+----------------
-- Jaipur    | 19           | 8               | 42.1           
-- Lucknow   | 49           | 15              | 30.6           
-- Bangalore | 33           | 8               | 24.2           
-- (3 rows)
SELECT c.city,
       COUNT(*)                                   AS total_orders,
       SUM(o.returned)                            AS returned_orders,
       ROUND(SUM(o.returned) * 100.0 / COUNT(*), 1) AS return_rate_pct
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.city
HAVING return_rate_pct > 20
ORDER BY return_rate_pct DESC;

-- ---------------------------------------------------------------------
-- e) Ranking with ORDER BY + LIMIT / OFFSET (3 marks)
-- ---------------------------------------------------------------------
-- Tie-break on customer_id ASC: if two customers have equal total_spend, the
-- order would otherwise be arbitrary, so LIMIT/OFFSET pages could differ between runs.
-- e1 = top 5; e2 = ranks 3-5 (skip 2, take 3) -> last three rows of e1, same order.
-- OUTPUT:
-- customer_id | name    | total_spend
-- ------------+---------+------------
-- C043        | Reyansh | 12920.00   
-- C026        | Isha    | 8371.60    
-- C008        | Meera   | 4564.60    
-- C011        | Arjun   | 4111.00    
-- C042        | Sanya   | 3785.00    
-- (5 rows)
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN products  p ON o.product_id  = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 5;

-- OUTPUT:
-- customer_id | name  | total_spend
-- ------------+-------+------------
-- C008        | Meera | 4564.60    
-- C011        | Arjun | 4111.00    
-- C042        | Sanya | 3785.00    
-- (3 rows)
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN products  p ON o.product_id  = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 3 OFFSET 2;

-- ---------------------------------------------------------------------
-- f) Three-table JOIN with GROUP BY: revenue by category (3 marks)
-- ---------------------------------------------------------------------
-- customers is joined (not strictly needed here) to confirm the 3-way join works for Part 3.
-- OUTPUT:
-- category     | order_count | category_revenue
-- -------------+-------------+-----------------
-- Haircare     | 54          | 44956.10        
-- Skincare     | 60          | 27346.00        
-- Babycare     | 30          | 16805.00        
-- PersonalCare | 36          | 10753.10        
-- (4 rows)
SELECT p.category,
       COUNT(o.order_id) AS order_count,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS category_revenue
FROM orders o
JOIN products  p ON o.product_id  = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY p.category
ORDER BY category_revenue DESC;

-- ---------------------------------------------------------------------
-- g) LIKE pattern match: customer names starting with 'A' (2 marks)
-- ---------------------------------------------------------------------
-- OUTPUT:
-- customer_id | name   | city     
-- ------------+--------+----------
-- C001        | Aarav  | Mumbai   
-- C003        | Aditi  | Mumbai   
-- C004        | Ananya | Lucknow  
-- C011        | Arjun  | Bangalore
-- C021        | Aryan  | Bangalore
-- C030        | Anika  | Bangalore
-- C031        | Aditya | Jaipur   
-- C036        | Aisha  | Delhi    
-- C041        | Ayaan  | Lucknow  
-- C044        | Aria   | Bangalore
-- (10 rows)
SELECT customer_id, name, city
FROM customers
WHERE name LIKE 'A%'
ORDER BY customer_id;

-- ---------------------------------------------------------------------
-- h) DISTINCT acquisition sources (1 mark)
-- ---------------------------------------------------------------------
-- OUTPUT:
-- acquisition_source
-- ------------------
-- Ad                
-- Organic           
-- Referral          
-- Social            
-- (4 rows)
SELECT DISTINCT acquisition_source
FROM customers
ORDER BY acquisition_source;

-- ---------------------------------------------------------------------
-- i) ALTER TABLE + UPDATE with CASE: loyalty tier (1 mark)
-- ---------------------------------------------------------------------
-- Note: ALTER TABLE fails if the column already exists. To re-run this file,
-- first re-run schema.sql + seed_data.sql (fresh tables).
ALTER TABLE customers ADD COLUMN loyalty_tier VARCHAR(10);

-- No WHERE clause: every customer row gets a value.
UPDATE customers
SET loyalty_tier = CASE WHEN city_tier = 1 THEN 'Gold' ELSE 'Silver' END;

-- OUTPUT:
-- loyalty_tier | customer_count
-- -------------+---------------
-- Gold         | 28            
-- Silver       | 17            
-- (2 rows)
SELECT loyalty_tier, COUNT(*) AS customer_count
FROM customers
GROUP BY loyalty_tier
ORDER BY loyalty_tier;
