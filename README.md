# 🌾 FarmBridge AI — Farm-to-Customer Marketplace

React (Create React App) + Django REST Framework + SQLite/MySQL. JWT auth, role-based permissions (customer / farmer / admin),
farmer KYC, per-farmer **order tracking**, **cash-on-delivery** checkout, reviews, and two scikit-learn models (demand + price).

> **Honest status**
> * The Django tests (`python manage.py test`) are written but were **not executed by the author** (no Django in the authoring sandbox).
>   The ML pipeline and the order state machine *were* executed and verified. Run the tests on your machine and report any failure.
> * ML models are trained on **synthetic demo data** (see `backend/ml_engine/README.md`).
> * Online payment (Razorpay) has been **removed**. Every order is cash on delivery.

## Project layout
```
farmbridge-ai/
├── backend/        Django project (settings in farmbridge/)
│   ├── accounts/  farms/  products/  cart/  orders/  reviews/  ml_engine/  common/
│   ├── media/ (public images)   private_media/ (private KYC files)
│   └── requirements.txt  requirements-mysql.txt  .env.example
├── frontend/       React app
├── docs/           architecture, database schema, API reference, Postman collection
└── README.md
```

## Quick start

Prerequisites: Python 3.10+ and Node 20+ (MySQL optional).

### Backend — Windows PowerShell
```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations accounts farms products cart orders reviews ml_engine
python manage.py migrate
python manage.py seed_data
python ml_engine/train_demand_model.py
python ml_engine/train_price_model.py
python manage.py runserver
```
macOS / Linux: use `python3 -m venv venv`, `source venv/bin/activate` and `cp` instead of `copy`.

**Schema changed — start from a clean database.** If you ran an earlier version (including the Razorpay one), delete
`backend/db.sqlite3` *and* every `backend/*/migrations/0*.py` file (keep each `__init__.py`), and delete the old `backend/payments/` folder, then run the commands above.

### Frontend (second terminal)
```powershell
cd frontend
copy .env.example .env
npm install
npm start
```
Open http://localhost:3000 (API runs on http://localhost:8000).

### Demo logins (password `Demo@12345`, development only)
`admin_demo` · `customer_demo` · `farmer_ravi` · `farmer_anita`. Seeded farms are pre-approved; real farmers go through KYC.
Admins cannot self-register; create one with `python manage.py createsuperuser`.

### MySQL (optional)
```sql
CREATE DATABASE farmbridge_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'farmbridge_user'@'localhost' IDENTIFIED BY 'a-strong-password';
GRANT ALL PRIVILEGES ON farmbridge_db.* TO 'farmbridge_user'@'localhost';
```
Set `DB_ENGINE=mysql` and the `DB_*` values in `backend/.env`, `pip install -r requirements-mysql.txt`, then migrate.
If `mysqlclient` fails to build on Windows: `pip install pymysql` and add `import pymysql` / `pymysql.install_as_MySQLdb()` at the top of `backend/farmbridge/__init__.py`.
Checkout uses `SELECT … FOR UPDATE` to prevent overselling; this really locks only on MySQL/PostgreSQL, not SQLite.

## How ordering and tracking work
1. The customer's cart lives on the server (prices always read from the database). Checkout builds an order from it, snapshots prices, reserves stock in one transaction, and splits it into **one shipment per farmer**. The order starts as `confirmed` with payment status `cod_pending`.
2. Statuses: `confirmed → processing → shipped → out_for_delivery → delivered`, or `cancelled` (only before shipping). Skipping steps is rejected (`backend/orders/state.py`).
3. Each farmer sees and updates **only their own** shipment (`POST /farmer/shipments/<id>/status/`, optional carrier and tracking number). The order status is derived from its shipments, so a two-farm order is "delivered" only when both are.
4. Customers see a progress bar per farmer and a timeline. They can cancel while nothing is processing; cancelling returns stock.
5. Cash: farmers cannot mark orders paid. An admin records collection of a delivered order (`POST /admin/orders/<id>/mark-cod-paid/`).

## Tests
```powershell
cd backend
python manage.py test
```
Covers auth/JWT/logout, role permissions, KYC approve/reject + private documents, products & ownership, cart, checkout (price/stock/atomicity), multi-farm tracking and transitions, COD collection, reviews, ML endpoints. The parallel-checkout test runs only on MySQL; ML tests skip until models are trained.

## API
All under `/api/v1/` — see `docs/api-documentation.md` and import `docs/FarmBridge.postman_collection.json` into Postman.
`auth/…` · `categories/` · `products/` · `farms/` · `farmer/{profile,kyc,dashboard,shipments}` · `cart/` · `orders/{checkout,<id>,<id>/cancel}` · `reviews/` · `ai/{demand-prediction,price-recommendation,model-info,history}` · `admin/{stats,users,kyc-applications,products,orders,shipments,reviews}`

## Security notes
JWT is kept in `localStorage` (simple, but XSS-sensitive; React escapes output and review text is tag-stripped). Refresh tokens rotate and are blacklisted on logout. Login/registration/prediction endpoints are rate-limited. KYC documents live in `private_media/` with no URL, are streamed only to their owner or an admin, and only the last 4 ID characters are stored. Uploads are checked for size, extension and real file signature. With `DEBUG=False` the app enforces HTTPS redirect, secure cookies, HSTS and refuses to start without `SECRET_KEY`. Never commit `.env`.

## Deployment
* **Backend:** `pip install -r requirements.txt`, set env vars (`DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, DB settings), `python manage.py migrate`, `collectstatic`, run `gunicorn farmbridge.wsgi`. Train the models on the server (joblib files are scikit-learn-version specific).
* **Database:** a local MySQL is not reachable from a cloud host. Use a managed MySQL with TLS, a least-privilege user and IP allow-listing.
* **Media:** cloud disks are often ephemeral. Product images need object storage (S3/Cloudinary via `django-storages`); `private_media/` (KYC) needs a persistent **private** volume or bucket (swap `get_private_storage()` in `farms/models.py`).
* **Frontend:** `npm run build`, host `build/` (Netlify/Vercel) with `REACT_APP_API_URL` pointing at the HTTPS API and an SPA fallback to `index.html`.

## Known limitations
Cash on delivery only; no email/SMS notifications (password-reset mail prints to the console); Contact form is a demo; no product photography included (a leaf placeholder shows); ML is a demo on synthetic data supporting only kg/quintal products and 10 crops; no automated frontend tests; migrations are generated locally on first run.

## Concepts in one minute
**Model** = Python class describing data · **table** = its storage in the DB · **migration** = versioned change script (`makemigrations` writes it, `migrate` applies it) · **ORM query** = Python like `Product.objects.filter(price__lt=100)` that Django turns into SQL.
