CREATE TABLE online_retail_raw (
    InvoiceNo VARCHAR(20),
    StockCode VARCHAR(20),
    Description TEXT,
    Quantity INT,
    InvoiceDate TIMESTAMP,
    UnitPrice NUMERIC,
    CustomerID INT,
    Country VARCHAR(50)
);

select * from online_retail_raw;

select count(*) from online_retail_raw;

----Data Cleaning
----1️⃣ Check NULL CustomerID
SELECT count(*) 
FROM online_retail_raw
WHERE CustomerID IS NULL;

----Remove NULL Customers
DELETE FROM online_retail_raw
WHERE CustomerID IS NULL;

----After deleting, verify
SELECT COUNT(*) 
FROM online_retail_raw
WHERE CustomerID IS NULL;

----🔹 Check Negative Records
SELECT *
FROM online_retail_raw
WHERE Quantity < 0;

----Check how many:
SELECT COUNT(*)
FROM online_retail_raw
WHERE Quantity < 0;

----Remove returns completely.
DELETE FROM online_retail_raw
WHERE Quantity <= 0;

----Remove Zero or Negative Price (Sometimes UnitPrice is 0.)
----Check:
SELECT *
FROM online_retail_raw
WHERE UnitPrice <= 0;

----If exists:
DELETE FROM online_retail_raw
WHERE UnitPrice <= 0;

----Remove Duplicate Records
----Check duplicates:
SELECT InvoiceNo, StockCode, CustomerID, COUNT(*)
FROM online_retail_raw
GROUP BY InvoiceNo, StockCode, CustomerID
HAVING COUNT(*) > 1;

----If duplicates exist:
DELETE FROM online_retail_raw a
USING online_retail_raw b
WHERE a.ctid < b.ctid
AND a.InvoiceNo = b.InvoiceNo
AND a.StockCode = b.StockCode
AND a.CustomerID = b.CustomerID;

----Format InvoiceDate Properly
----Since you created it as TIMESTAMP, verify format:
SELECT InvoiceDate
FROM online_retail_raw
LIMIT 10;

----Add revenue Column
----Now calculate revenue.
ALTER TABLE online_retail_raw
ADD COLUMN revenue DECIMAL(10,2);

----Update values:
UPDATE online_retail_raw
SET revenue = Quantity * UnitPrice;

----Verify:
SELECT Quantity, UnitPrice, revenue
FROM online_retail_raw
LIMIT 10;

----Create fact_sales Table
CREATE TABLE fact_sales (
    invoice_no VARCHAR(20),
    customer_id INT,
    product_id VARCHAR(20),
    date_id DATE,
    quantity INT,
    revenue NUMERIC
);

----Populate Fact Table
INSERT INTO fact_sales
SELECT
    InvoiceNo,
    CustomerID,
    StockCode,
    InvoiceDate::DATE,
    Quantity,
    Quantity * UnitPrice
FROM online_retail_raw;

drop table fact_sales;
select * from fact_sales;

select * from online_retail_raw;

----create Dim_Product table
CREATE TABLE dim_product (
    product_id VARCHAR(20) PRIMARY KEY,
    product_name TEXT
);
----Populate dim_product
INSERT INTO dim_product (product_id, product_name)
SELECT 
    StockCode,
    MAX(Description)  -- or MIN(Description)
FROM online_retail_raw
GROUP BY StockCode;

select * from dim_Product;
drop table dim_Product;

----✅ How To Check Duplicate Products
SELECT StockCode, COUNT(DISTINCT Description)
FROM online_retail_raw
GROUP BY StockCode
HAVING COUNT(DISTINCT Description) > 1;

----create dim_customer table
CREATE TABLE dim_customer (
    customer_id INT PRIMARY KEY,
    country VARCHAR(50),
    first_purchase_date DATE,
    total_orders INT
);

----Populate dim_customer
INSERT INTO dim_customer
SELECT
    CustomerID,
    MAX(Country),
    MIN(InvoiceDate)::DATE,
    COUNT(DISTINCT InvoiceNo)
FROM online_retail_raw
GROUP BY CustomerID;

select * from dim_customer;
drop table dim_customer;

----📦 create table Dim_Date
CREATE TABLE dim_date (
    date_id DATE PRIMARY KEY,
    year INT,
    month INT,
    quarter INT
);

----Populate dim_date
INSERT INTO dim_date
SELECT DISTINCT
    InvoiceDate::DATE,
    EXTRACT(YEAR FROM InvoiceDate),
    EXTRACT(MONTH FROM InvoiceDate),
    EXTRACT(QUARTER FROM InvoiceDate)
FROM online_retail_raw;

select * from dim_date;

----Add Foreign Keys
ALTER TABLE fact_sales
ADD CONSTRAINT fk_customer
FOREIGN KEY (customer_id)
REFERENCES dim_customer(customer_id);

ALTER TABLE fact_sales
ADD CONSTRAINT fk_product
FOREIGN KEY (product_id)
REFERENCES dim_product(product_id);

ALTER TABLE fact_sales
ADD CONSTRAINT fk_date
FOREIGN KEY (date_id)
REFERENCES dim_date(date_id);

----Create Indexes (Performance Optimization)
CREATE INDEX idx_fact_customer ON fact_sales(customer_id);
CREATE INDEX idx_fact_product ON fact_sales(product_id);
CREATE INDEX idx_fact_date ON fact_sales(date_id);

----✅ Validation Queries
SELECT COUNT(*) FROM fact_sales;
SELECT COUNT(*) FROM dim_customer;
SELECT COUNT(*) FROM dim_product;
SELECT COUNT(*) FROM dim_date;

----Create "Single Customer View" (Advanced SQL View)
CREATE VIEW single_customer_view AS
SELECT 
    CustomerID,
    MIN(InvoiceDate) AS FirstPurchase,
    MAX(InvoiceDate) AS LastPurchase,
    COUNT(DISTINCT InvoiceNo) AS TotalOrders,
    SUM(Quantity) AS TotalQuantity,
    SUM(Quantity * UnitPrice) AS TotalRevenue
FROM online_retail_raw
GROUP BY CustomerID;

select * from single_customer_view;

----Query Performance Check
CREATE INDEX idx_customer ON online_retail_raw(CustomerID);
CREATE INDEX idx_invoice ON online_retail_raw(InvoiceNo);

----RFM SEGMENTATION (Core Intelligence)
----Export Data to Python
SELECT 
CustomerID,
InvoiceNo,
InvoiceDate,
Quantity * UnitPrice AS Revenue
FROM online_retail_raw;

select * from fact_sales;




