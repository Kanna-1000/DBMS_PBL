# Property Rental and Lease Management System
DBMS PBL project - Woxsen University, School of Technology (CSE AIML, Rhinos). Python (Flask) + MySQL 8.0.

**Student:** Pakanati Priyakaran Reddy (25WU0101090) | **Faculty:** Dr. Sahithi

## Repository contents
| Path | Description |
|---|---|
| `presentations/Review1_Presentation.pptx` | Review 1 - problem statement, solution strategy, ER diagram |
| `presentations/Review2_Presentation.pptx` | Review 2 - logical design, normalization, data dictionary |
| `presentations/Review3_Final_Presentation.pptx` | Review 3 - final prototype, testing, results |
| `prototype/index.html` | Working prototype "Reddy's Estate" - open in any browser |
| `app.py`, `requirements.txt` | Flask + MySQL version (add, search, edit, remove) |
| `property_rental_schema.sql` | Database script: tables, constraints, sample data, report queries |
| `screenshots/` | Screenshots of the prototype and the Flask app |
| `docs/Video_Presentation_Link.md` | Public Google Drive link to the 5-minute video presentation |
| `Property_Rental_PBL_Report.pdf` | Final report |

## Open the prototype
Double-click `prototype/index.html` (no installation needed; data is stored in the browser).

## Run the Flask + MySQL version
1. `pip install -r requirements.txt`
2. `mysql -u root -p < property_rental_schema.sql`
3. Optional credentials: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
4. `python app.py` and open http://127.0.0.1:5000

## Features
Add / view / search / edit / remove records for six modules, lease date validation, blocked deletes on referenced records, dashboard with occupancy by type, monthly revenue and overdue rent.
