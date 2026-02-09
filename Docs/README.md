# InvoiceMind Documentation

> Local-LLM, Evidence-first, Audit-ready Invoice Processing

این فایل تنها مرجع مستندات پروژه `InvoiceMind` است و جایگزین تمام گزارش‌های قبلی داخل پوشه `Docs` شده است.

## 1) معرفی پروژه

`InvoiceMind` یک سامانه پردازش هوشمند فاکتور با معماری Local-First است که کل مسیر پردازش سند را از ورودی تا خروجی قابل ممیزی پوشش می‌دهد:

- دریافت سند (PDF / Image / XLSX)
- اعتبارسنجی قرارداد کیفیت داده
- استخراج ساختاریافته
- تصمیم‌گیری خودکار یا ارجاع به بازبینی انسانی
- ثبت رویدادها در زنجیره Audit
- خروجی استاندارد برای مصرف در سیستم‌های مالی

این پروژه دو‌زبانه (فارسی/انگلیسی) است و UI در هر دو زبان قابل استفاده است.

## 2) اهداف فنی

- اجرای کامل محلی (بدون وابستگی اجباری به API بیرونی)
- کیفیت قابل دفاع با quality gates و reason codes
- قابلیت رهگیری با audit trail
- مقیاس‌پذیری مرحله‌ای با worker/background mode
- تجربه کاربری عملیاتی برای تیم Review

## 3) معماری کلان

### Backend

- Framework: `FastAPI`
- DB: `SQLite` (قابل ارتقا)
- ORM/Migrations: `SQLAlchemy` + `Alembic`
- لایه‌ها:
  - API Routers
  - Services (extraction, policy, governance, change-management)
  - Orchestrator برای مدیریت چرخه Run
  - Storage (raw/runs/audit/quarantine)

### Frontend

- Framework: `Next.js` (App Router) + `React` + `TypeScript`
- مسیرهای عملیاتی:
  - داشبورد
  - آپلود
  - Runs
  - Quarantine
  - Governance
  - Settings
- پشتیبانی همزمان `fa` و `en` با RTL/LTR

### مسیر پردازش

`Ingestion -> Validation -> Extraction -> Gating -> (Auto-Approve | Needs-Review) -> Finalize/Export`

## 4) ساختار پروژه

```text
InvoiceMind/
├─ app/                       # هسته بک‌اند
│  ├─ routers/                # API endpoints
│  ├─ services/               # business logic
│  ├─ orchestrator.py         # run lifecycle orchestration
│  ├─ models.py               # دیتامدل
│  ├─ config.py               # تنظیمات runtime
│  └─ main.py                 # entrypoint
├─ frontend/                  # رابط کاربری Next.js
├─ config/                    # نسخه‌های فعال prompt/template/policy/routing/model
├─ scripts/                   # ابزارهای اجرایی (مثل migrate)
├─ tests/                     # تست‌های backend
├─ tools/                     # ابزارهای eval/perf
├─ models.yaml                # کاتالوگ مدل‌های لوکال
├─ run.bat                    # اجرای همزمان فرانت و بک روی ویندوز
├─ .env.example               # نمونه env بک‌اند
└─ frontend/.env.local.example # نمونه env فرانت
```

## 5) پیش‌نیازها

- Python `3.11+`
- Node.js `22+`
- npm
- (اختیاری) Ollama برای اجرای مدل‌های GGUF

## 6) راه‌اندازی سریع

### روش یک‌کلیکی (ویندوز)

در ریشه پروژه:

```bat
run.bat
```

این فایل:
- migration را اجرا می‌کند
- backend را روی `http://127.0.0.1:8000` بالا می‌آورد
- frontend را روی `http://127.0.0.1:3000` بالا می‌آورد

### روش دستی

#### Backend

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/migrate.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

#### Frontend

```powershell
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## 7) تنظیمات محیطی (Environment)

### بک‌اند

از فایل نمونه کپی بگیرید:

```powershell
Copy-Item .env.example .env
```

متغیرهای مهم:

- `INVOICEMIND_DB_URL`: مسیر دیتابیس
- `INVOICEMIND_STORAGE_ROOT`: مسیر ذخیره‌سازی artifacts
- `INVOICEMIND_EXECUTION_MODE`: `background | worker | hybrid`
- `INVOICEMIND_LOW_CONFIDENCE_THRESHOLD`
- `INVOICEMIND_REQUIRED_FIELD_COVERAGE_THRESHOLD`
- `INVOICEMIND_EVIDENCE_COVERAGE_THRESHOLD`
- `INVOICEMIND_PROMPT_VERSION`
- `INVOICEMIND_TEMPLATE_VERSION`
- `INVOICEMIND_ROUTING_VERSION`
- `INVOICEMIND_POLICY_VERSION`
- `INVOICEMIND_MODEL_VERSION`
- `INVOICEMIND_MODEL_RUNTIME` (پیشنهادی: `local`)
- `INVOICEMIND_MODEL_QUANTIZATION`

### فرانت‌اند

از فایل نمونه کپی بگیرید:

```powershell
Copy-Item frontend/.env.local.example frontend/.env.local
```

متغیرهای مهم:

- `INVOICEMIND_API_BASE_URL` (مثال: `http://localhost:8000`)
- `INVOICEMIND_API_USERNAME`
- `INVOICEMIND_API_PASSWORD`

## 8) راهنمای مدل‌های Local LLM

### اصل مهم

این پروژه برای Local Inference طراحی شده و نیاز به API خارجی ندارد.

### محل تعریف و مدیریت مدل‌ها

- `models.yaml`
  - فهرست مدل‌ها، نقش هر مدل، فرمت و برآورد مصرف VRAM
- `config/active_versions.yaml`
  - نگهداری نسخه فعال runtime برای policy/template/model/routing
- `config/models/<MODEL_VERSION>/model.yaml`
  - متادیتای نسخه مدل فعال

### محل فایل وزن مدل‌ها (weights)

پیشنهاد عملی:
- در سیستم محلی یک مسیر ثابت برای weights داشته باشید (مثلا `D:\LLMModels`)
- این فایل‌ها را داخل ریپازیتوری قرار ندهید
- فقط متادیتا/نام مدل در `models.yaml` و تنظیمات env نگهداری شود

### اجرای مدل‌های GGUF با Ollama (اختیاری)

نمونه جریان کار:

```powershell
ollama import <path_to_gguf_file> --name invoicemind-extractor
ollama run invoicemind-extractor --prompt "extract invoice fields"
```

### انتخاب مدل در runtime

- `INVOICEMIND_MODEL_VERSION` باید با نسخه‌های تعریف‌شده در `config/models` هم‌راستا باشد
- `INVOICEMIND_MODEL_RUNTIME=local`
- `INVOICEMIND_MODEL_QUANTIZATION` مطابق سخت‌افزار (مثلا `q4`)

## 9) APIهای اصلی بک‌اند

### Health

- `GET /health`
- `GET /ready`
- `GET /metrics`

### Auth

- `POST /v1/auth/token`

### Documents

- `POST /v1/documents`
- `GET /v1/documents/{document_id}`

### Runs

- `POST /v1/documents/{document_id}/runs`
- `GET /v1/runs/{run_id}`
- `POST /v1/runs/{run_id}/cancel`
- `POST /v1/runs/{run_id}/replay`
- `GET /v1/runs/{run_id}/export`

### Quarantine

- `GET /v1/quarantine`
- `GET /v1/quarantine/{item_id}`
- `POST /v1/quarantine/{item_id}/reprocess`

### Governance / Audit

- `GET /v1/audit/verify`
- `GET /v1/audit/events`
- `GET /v1/governance/runtime-versions`
- `POST /v1/governance/change-risk`
- `POST /v1/governance/capacity-estimate`

## 10) مسیرهای UI

پس از اجرای فرانت:

- Landing: `http://127.0.0.1:3000`
- English Dashboard: `http://127.0.0.1:3000/en/dashboard`
- Persian Dashboard: `http://127.0.0.1:3000/fa/dashboard`
- Upload: `/{lang}/upload`
- Runs: `/{lang}/runs`
- Quarantine: `/{lang}/quarantine`
- Governance: `/{lang}/governance`
- Settings: `/{lang}/settings`

## 11) مسیرهای داده و Artifact

طبق تنظیم پیش‌فرض `INVOICEMIND_STORAGE_ROOT=app/storage`:

- `app/storage/raw` فایل خام ورودی
- `app/storage/runs` خروجی‌ها و artifactهای پردازش
- `app/storage/quarantine` اسناد quarantine شده
- `app/storage/audit` رویدادهای audit

نکته:
- این پوشه‌ها runtime artifact هستند و نباید وارد push ریپازیتوری شوند.

## 12) تست و کنترل کیفیت

### Backend

```powershell
pytest
```

### Frontend

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

### چک نهایی پیش از انتشار

- backend up و health endpoints سبز
- frontend build بدون خطا
- مسیرهای `/fa/*` و `/en/*` در دسترس
- upload -> run -> review/quarantine -> export قابل انجام
- `GET /v1/audit/verify` وضعیت معتبر برگرداند

## 13) راهنمای انتشار روی GitHub

### فایل‌هایی که باید Push شوند

- کد backend/frontend
- اسکریپت‌ها (`scripts`, `tools`)
- تنظیمات نمونه (`.env.example`, `frontend/.env.local.example`)
- `README.md`, `LICENSE`, `SECURITY.md`
- این سند: `Docs/README.md`

### فایل‌هایی که نباید Push شوند

- env واقعی (`.env`, `frontend/.env.local`)
- دیتابیس‌های محلی (`*.db`, `*.sqlite*`)
- storage runtime (`app/storage`, `test_storage`, `e2e_storage`, `perf_storage`)
- `frontend/node_modules`, `frontend/.next`
- مدل‌های وزن‌دار محلی (GGUF/safetensors) و هر فایل حجیم محرمانه

## 14) عیب‌یابی سریع

### فرانت بالا می‌آید ولی دیتا ندارد

- `INVOICEMIND_API_BASE_URL` را بررسی کنید
- backend باید روی `:8000` فعال باشد
- endpoint `GET /health` پاسخ `ok` بدهد

### خطای احراز هویت در UI

- مقدار `INVOICEMIND_API_USERNAME` و `INVOICEMIND_API_PASSWORD` در `frontend/.env.local`
- endpoint `POST /v1/auth/token` را مستقیم تست کنید

### خطای migration

- `python scripts/migrate.py` را مجدد اجرا کنید
- مسیر `INVOICEMIND_DB_URL` معتبر باشد

### مصرف RAM/VRAM بالا در مدل

- quantization سبک‌تر انتخاب کنید (`q4`)
- مدل کوچک‌تر از `models.yaml` فعال کنید
- اجرای heavy model را به batch/offline محدود کنید

## 15) استاندارد عملیاتی پروژه

- نام رسمی پروژه در تمام اسناد و تنظیمات: `InvoiceMind`
- تغییرات نسخه‌های policy/prompt/template/model/routing باید همزمان در config و env هماهنگ شوند
- قبل از انتشار، تست‌های backend/frontend و کنترل audit الزامی است

---

اگر نیاز به توسعه قابلیت جدید دارید، همین فایل باید به‌روز شود تا مستندات پروژه تک‌منبعه و سازگار باقی بماند.
