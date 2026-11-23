-- Spoke & Sprocket, an invented online bike-parts store. All people and data are made up.
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, zip TEXT);
CREATE TABLE products (
  sku TEXT PRIMARY KEY, name TEXT, category TEXT, price_cents INTEGER, stock INTEGER, final_sale INTEGER
);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY, customer_id INTEGER, status TEXT, order_date TEXT, delivered_date TEXT
);
CREATE TABLE order_items (
  order_id INTEGER, sku TEXT, qty INTEGER, price_cents INTEGER,
  returned_qty INTEGER DEFAULT 0, exchanged_qty INTEGER DEFAULT 0,
  PRIMARY KEY (order_id, sku)
);
CREATE TABLE returns (
  id INTEGER PRIMARY KEY, order_id INTEGER, sku TEXT, qty INTEGER, refund_cents INTEGER, created TEXT
);
CREATE TABLE exchanges (
  id INTEGER PRIMARY KEY, order_id INTEGER, old_sku TEXT, new_sku TEXT, created TEXT
);

INSERT INTO customers VALUES
 (1, 'Ana Ruiz', 'ana.ruiz@mail.test', '97201'),
 (2, 'Ben Okafor', 'ben.okafor@mail.test', '60614'),
 (3, 'Chloe Park', 'chloe.park@mail.test', '30307'),
 (4, 'Dev Patel', 'dev.patel@mail.test', '78704'),
 (5, 'Erin Walsh', 'erin.walsh@mail.test', '02139'),
 (6, 'Farid Haddad', 'farid.h@mail.test', '98103'),
 (7, 'Gina Moretti', 'gina.m@mail.test', '11215'),
 (8, 'Hugo Lind', 'hugo.lind@mail.test', '55408');

INSERT INTO products VALUES
 ('CH-11', 'KMC X11 chain', 'chain', 3499, 12, 0),
 ('CH-12', 'Shimano 12-speed chain', 'chain', 3499, 0, 0),
 ('CH-10', 'SRAM PC-1031 chain', 'chain', 3499, 5, 0),
 ('TR-28', 'Gravel tire 700x40', 'tire', 4999, 8, 0),
 ('TR-32', 'Road tire 700x28', 'tire', 4999, 6, 0),
 ('TR-25', 'Commuter tire 700x35', 'tire', 3999, 4, 0),
 ('BR-01', 'Hydraulic brake pads', 'brakes', 1899, 20, 0),
 ('BR-02', 'Organic brake pads', 'brakes', 1899, 0, 0),
 ('SD-01', 'Comfort saddle', 'saddle', 5999, 3, 0),
 ('SD-02', 'Race saddle', 'saddle', 5999, 2, 0),
 ('LT-01', 'USB front light', 'light', 2499, 10, 1),
 ('LT-02', 'Rear radar light', 'light', 8999, 4, 0),
 ('PD-01', 'Flat pedals', 'pedals', 4499, 7, 0),
 ('PD-02', 'Clipless pedals', 'pedals', 8999, 5, 0);

INSERT INTO orders VALUES
 (1001, 1, 'delivered', '2026-06-01', '2026-06-05'),
 (1002, 2, 'processing', '2026-06-13', NULL),
 (1003, 3, 'delivered', '2026-04-20', '2026-04-25'),
 (1004, 4, 'shipped', '2026-06-11', NULL),
 (1005, 5, 'delivered', '2026-06-02', '2026-06-06'),
 (1006, 6, 'delivered', '2026-05-10', '2026-05-14'),
 (1007, 7, 'delivered', '2026-06-08', '2026-06-10'),
 (1008, 8, 'delivered', '2026-05-20', '2026-05-24'),
 (1009, 1, 'processing', '2026-06-14', NULL),
 (1010, 3, 'delivered', '2026-06-01', '2026-06-03');

INSERT INTO order_items (order_id, sku, qty, price_cents) VALUES
 (1001, 'CH-11', 1, 3499), (1001, 'BR-01', 2, 1899),
 (1002, 'TR-28', 2, 4999),
 (1003, 'SD-01', 1, 5999),
 (1004, 'PD-02', 1, 8999),
 (1005, 'LT-01', 1, 2499), (1005, 'TR-32', 1, 4999),
 (1006, 'CH-10', 1, 3499),
 (1007, 'TR-28', 1, 4999),
 (1008, 'SD-02', 1, 5999), (1008, 'PD-01', 1, 4499),
 (1009, 'LT-02', 1, 8999),
 (1010, 'CH-11', 2, 3499);
