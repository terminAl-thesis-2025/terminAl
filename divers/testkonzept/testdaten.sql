-- Testdaten für die usertest-Tabelle
-- Fügt 15 Beispiel-Datensätze für Mitarbeiter hinzu

-- Löschen vorhandener Daten (falls nötig)
TRUNCATE TABLE usertest;

-- Zurücksetzen der Sequenz für die ID (falls vorhanden)
-- ALTER SEQUENCE usertest_id_seq RESTART WITH 1;

-- Einfügen der Testdaten
INSERT INTO usertest (id, name, abteilung, gehalt, einstellungsdatum) VALUES
(1, 'Anna Schmidt', 'Entwicklung', 65000.00, '2022-03-15'),
(2, 'Peter Müller', 'Entwicklung', 72000.00, '2023-02-01'),
(3, 'Maria Weber', 'Marketing', 58000.00, '2021-10-10'),
(4, 'Thomas Becker', 'Finanzen', 82000.00, '2020-05-20'),
(5, 'Laura Klein', 'Entwicklung', 69500.00, '2023-04-12'),
(6, 'Michael Schulz', 'Personalwesen', 61000.00, '2022-08-30'),
(7, 'Sophie Hoffmann', 'Marketing', 55000.00, '2023-01-15'),
(8, 'Jan Wagner', 'Entwicklung', 78000.00, '2021-11-05'),
(9, 'Katharina Fischer', 'Finanzen', 85000.00, '2023-03-22'),
(10, 'Daniel Meyer', 'Entwicklung', 71000.00, '2023-07-01'),
(11, 'Lisa Schneider', 'Personalwesen', 59500.00, '2022-09-18'),
(12, 'David Bauer', 'Marketing', 57000.00, '2021-06-30'),
(13, 'Julia Richter', 'Entwicklung', 68000.00, '2023-05-08'),
(14, 'Markus Wolf', 'Finanzen', 79000.00, '2022-11-12'),
(15, 'Sarah Neumann', 'Entwicklung', 74500.00, '2023-02-28');

-- Bestätigung der Datenimportierung
SELECT 'Testdaten wurden erfolgreich importiert: ' || COUNT(*) || ' Datensätze.' AS import_status FROM usertest;