-- Clip & Curl, an invented hair salon. All people and data are made up.
CREATE TABLE clients (id INTEGER PRIMARY KEY, name TEXT, phone TEXT UNIQUE);
CREATE TABLE stylists (id INTEGER PRIMARY KEY, name TEXT, level TEXT);
CREATE TABLE services (
  code TEXT PRIMARY KEY, name TEXT, minutes INTEGER, price_cents INTEGER, deposit_cents INTEGER, needs_senior INTEGER
);
CREATE TABLE bookings (
  id INTEGER PRIMARY KEY, client_id INTEGER, stylist_id INTEGER, service_code TEXT, start TEXT,
  status TEXT, deposit_cents INTEGER, deposit_status TEXT, reschedules INTEGER DEFAULT 0
);

INSERT INTO clients VALUES
 (1, 'Iris Chen', '555-0101'),
 (2, 'Jon Bell', '555-0102'),
 (3, 'Kara Diaz', '555-0103'),
 (4, 'Leo Novak', '555-0104'),
 (5, 'Maya Singh', '555-0105'),
 (6, 'Nate Ford', '555-0106'),
 (7, 'Olga Petrov', '555-0107');

INSERT INTO stylists VALUES (1, 'Rosa', 'senior'), (2, 'Sam', 'junior'), (3, 'Tara', 'senior');

INSERT INTO services VALUES
 ('CUT', 'Haircut', 60, 4500, 0, 0),
 ('BLOW', 'Blowout', 60, 3500, 0, 0),
 ('COLOR', 'Full color', 60, 12000, 3000, 1),
 ('BAL', 'Balayage', 60, 18000, 5000, 1);

INSERT INTO bookings VALUES
 (101, 1, 1, 'COLOR', '2026-06-18 14:00', 'booked', 3000, 'held', 0),
 (102, 2, 2, 'CUT', '2026-06-15 15:00', 'booked', 0, 'none', 0),
 (103, 3, 3, 'BAL', '2026-06-16 09:00', 'booked', 5000, 'held', 0),
 (104, 4, 1, 'COLOR', '2026-06-20 11:00', 'booked', 3000, 'held', 1),
 (105, 5, 2, 'BLOW', '2026-06-17 10:00', 'booked', 0, 'none', 0),
 (106, 6, 2, 'CUT', '2026-05-02 10:00', 'no_show', 0, 'none', 0),
 (107, 6, 3, 'CUT', '2026-05-30 12:00', 'no_show', 0, 'none', 0),
 (108, 7, 3, 'CUT', '2026-06-19 13:00', 'booked', 0, 'none', 0),
 (109, 1, 1, 'CUT', '2026-05-01 10:00', 'completed', 0, 'none', 0),
 (110, 3, 1, 'COLOR', '2026-05-20 15:00', 'completed', 3000, 'refunded', 0);
