-- Forkful, an invented meal-kit subscription. All people and data are made up.
CREATE TABLE plans (code TEXT PRIMARY KEY, name TEXT, meals INTEGER, servings INTEGER, price_cents INTEGER);
CREATE TABLE subscribers (
  id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, zip TEXT, plan_code TEXT, status TEXT, paused_until TEXT
);
CREATE TABLE deliveries (
  id INTEGER PRIMARY KEY, subscriber_id INTEGER, date TEXT, status TEXT, issue TEXT
);
CREATE TABLE credits (
  id INTEGER PRIMARY KEY, subscriber_id INTEGER, delivery_id INTEGER, amount_cents INTEGER, created TEXT
);

INSERT INTO plans VALUES
 ('DUO3', 'Duo 3 meals', 3, 2, 6000),
 ('DUO4', 'Duo 4 meals', 4, 2, 7600),
 ('FAM3', 'Family 3 meals', 3, 4, 10500),
 ('FAM4', 'Family 4 meals', 4, 4, 13600);

INSERT INTO subscribers VALUES
 (1, 'Pia Lopez', 'pia.l@mail.test', '94110', 'DUO3', 'active', NULL),
 (2, 'Quinn Ross', 'quinn.r@mail.test', '80205', 'FAM4', 'active', NULL),
 (3, 'Rhea Nair', 'rhea.n@mail.test', '19104', 'DUO4', 'paused', '2026-07-06'),
 (4, 'Sol Kim', 'sol.kim@mail.test', '85004', 'FAM3', 'active', NULL),
 (5, 'Tess Grant', 'tess.g@mail.test', '37203', 'DUO3', 'active', NULL),
 (6, 'Uma Shah', 'uma.s@mail.test', '43215', 'DUO4', 'active', NULL);

INSERT INTO deliveries VALUES
 (201, 1, '2026-06-11', 'delivered', 'two meals arrived without ice packs'),
 (202, 1, '2026-06-18', 'scheduled', NULL),
 (203, 1, '2026-06-25', 'scheduled', NULL),
 (211, 2, '2026-05-28', 'delivered', 'box arrived crushed'),
 (212, 2, '2026-06-18', 'scheduled', NULL),
 (213, 2, '2026-06-25', 'scheduled', NULL),
 (221, 3, '2026-06-04', 'delivered', NULL),
 (231, 4, '2026-06-11', 'delivered', 'one meal was missing'),
 (232, 4, '2026-06-18', 'scheduled', NULL),
 (233, 4, '2026-06-25', 'scheduled', NULL),
 (241, 5, '2026-06-04', 'delivered', 'the salmon was spoiled'),
 (242, 5, '2026-06-18', 'scheduled', NULL),
 (243, 5, '2026-06-25', 'scheduled', NULL),
 (251, 6, '2026-06-11', 'delivered', NULL),
 (252, 6, '2026-06-18', 'scheduled', NULL),
 (253, 6, '2026-06-25', 'scheduled', NULL);

INSERT INTO credits VALUES (301, 4, 231, 3500, '2026-06-12');
