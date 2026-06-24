# Polyglot to Django Migration Guide

This guide covers when and how to migrate a Polyglot application to Django.
It assumes you have read the SPEC and understand how the Polyglot complexity
ladder works.

## Table of Contents

- [When to Migrate](#when-to-migrate)
- [The Complexity Ladder](#the-complexity-ladder)
- [Mapping Polyglot Concepts to Django](#mapping-polyglot-concepts-to-django)
- [Step-by-Step Migration](#step-by-step-migration)
- [Directory Mapping](#directory-mapping)
- [Common Pitfalls](#common-pitfalls)
- [Why Polyglot Makes Migration Easier](#why-polyglot-makes-migration-easier)

---

## When to Migrate

Django is the right choice when your application exhibits one or more of these
characteristics:

### Metadata-Heavy Systems

If your application has 20+ models with complex relationships, Django's
admin UI provides instant CRUD interfaces, inline editing, filtering,
search, and bulk actions — all without writing any UI code.

### Admin-Heavy Systems

If internal staff need to manage data through a web UI, Django Admin
(especially with `django-import-export`, `django-admin-actions`, and
custom admin views) is unmatched in developer productivity.

### Deep Workflow/FMS Demands

If your application has complex state machines (beyond what Polyglot's
`fsm_workflows` template provides), Django packages like `django-fsm`,
`django-viewflow`, and `django-river` offer production-proven workflow
engines with admin integration.

### Signal: You're building admin views by hand

If you find yourself writing CRUD forms, data tables, and filters in
FastAPI + Jinja2 templates that look like Django Admin, you've crossed
the threshold. Django Admin gives you all of that for free.

---

## The Complexity Ladder

Polyglot is designed with a complexity ladder. Each rung represents
increasing application demands:

```
Rung 0: Pure FastAPI + SQLAlchemy
  └─ Good for: Microservices, API-only, simple CRUD

Rung 1: Polyglot Templates (smtp, file_storage, websockets, etc.)
  └─ Good for: Adding standard capabilities without reinventing

Rung 2: Custom components + workflows
  └─ Good for: Domain-specific logic on top of established patterns

Rung 3: Django Upgrade (you are here)
  └─ When: Admin, metadata, workflows outgrow Polyglot's sweet spot
```

The key insight: **you don't have to choose between Polyglot and Django
at the start.** Start with Polyglot. When you hit Rung 3, the migration
path is well-understood because both systems follow similar architecture
patterns.

---

## Mapping Polyglot Concepts to Django

### FastAPI Route → Django View / ViewSet

```
Polyglot (FastAPI):
@app.get("/api/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    ...

Django (DRF ViewSet):
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
```

If using `django-ninja` (which mirrors FastAPI's decorator style):

```python
# Nearly identical syntax!
@api.get("/users")
def list_users(request):
    return User.objects.all()
```

### SQLAlchemy Model → Django Model

```
Polyglot (SQLAlchemy):
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True)

Django:
class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    email = models.EmailField(unique=True, max_length=255)
```

### Procrastinate Task → Celery / Django Q

```
Polyglot (Procrastinate):
@task_app.task(name="my_task")
def my_task(arg: str):
    ...

Django (Celery):
@app.task
def my_task(arg: str):
    ...

Django (Django Q — lighter alternative):
from django_q.tasks import async_task
async_task("myapp.tasks.my_task", "hello")
```

### Pydantic Schema → Django / DRF Serializer

```
Polyglot (Pydantic):
class UserCreate(BaseModel):
    email: str
    name: str | None = None

Django (DRF):
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "name"]
```

### Jinja2 Template → Django Template

Jinja2 and Django templates are syntactically similar. Key differences:

| Feature | Jinja2 | Django |
|---------|--------|--------|
| Loop | `{% for x in items %}` | `{% for x in items %}` (same) |
| If | `{% if x %}` | `{% if x %}` (same) |
| Filter | `{{ value\|upper }}` | `{{ value\|upper }}` (same) |
| Macro | `{% macro %}` | `{% include %}` or `{% block %}` |
| Context | Explicit | `render(request, context)` |
| URL | `{{ url_for() }}` | `{% url 'name' %}` |

---

## Step-by-Step Migration

### Phase 1: Models and Migrations

**Goal**: Recreate all Polyglot models as Django models with matching
table structures.

1. Create a new Django app within your project: `python manage.py startapp core`
2. For each Polyglot model, create an equivalent Django model
3. Use `inspectdb` to introspect existing Postgres tables:
   ```bash
   python manage.py inspectdb > core/models.py
   ```
4. Tweak the auto-generated models to add modern Django features (Meta options,
   custom managers, etc.)
5. Run `python manage.py makemigrations` (these will be "initial" migrations)
6. Apply with `python manage.py migrate --fake-initial` (Django recognizes
   existing tables)

### Phase 2: Admin UI

**Goal**: Instant admin CRUD with import/export.

1. Register all models in `admin.py`:
   ```python
   from django.contrib import admin
   from .models import User, WorkflowDefinition

   @admin.register(User)
   class UserAdmin(admin.ModelAdmin):
       list_display = ["email", "display_name"]
       search_fields = ["email"]

   @admin.register(WorkflowDefinition)
   class WorkflowAdmin(admin.ModelAdmin):
       list_display = ["name"]
   ```

2. Install `django-import-export` for CSV/XLSX import/export:
   ```bash
   pip install django-import-export
   ```

3. Add import/export mixin to all admin classes:
   ```python
   from import_export.admin import ImportExportModelAdmin

   @admin.register(User)
   class UserAdmin(ImportExportModelAdmin):
       ...
   ```

### Phase 3: API with DRF or Django Ninja

**Goal**: Recreate the API surface with Django REST Framework or Django Ninja.

**Option A: Django REST Framework (DRF)** — most popular, great for CRUD

```python
# serializers.py
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"

# views.py
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
```

**Option B: Django Ninja** — FastAPI-style decorator syntax

```python
from ninja import NinjaAPI, Schema

api = NinjaAPI()

class UserSchema(Schema):
    email: str
    name: str | None = None

@api.post("/users")
def create_user(request, payload: UserSchema):
    user = User.objects.create(**payload.dict())
    return {"id": user.id}
```

### Phase 4: Task Migration

**Goal**: Move Procrastinate tasks to Celery or Django Q.

**Celery setup** (standard option):
```python
# celery.py
from celery import Celery
app = Celery("myproject")
app.config_from_object("django.conf:settings", namespace="CELERY")

# tasks.py
from .celery import app
@app.task
def send_welcome_email(user_id: str):
    ...
```

**Django Q setup** (lighter option, uses Django ORM as broker):
```python
# tasks.py
from django_q.tasks import async_task
async_task("myapp.tasks.send_welcome_email", user_id)
```

### Phase 5: Cut-Over

**Goal**: Run Django alongside FastAPI during transition, then switch.

1. **COEXIST mode** (recommended):
   - Run Django on port 8001, FastAPI on 8000
   - Route `/admin/*` and `/api/*` to Django via nginx
   - Keep FastAPI for existing routes during migration
   - Gradually move routes to Django

2. **BIG BANG mode** (simple projects):
   - Deploy Django on port 8000
   - Replace the FastAPI Dockerfile
   - Verify all endpoints respond correctly

---

## Directory Mapping

| Polyglot | Django Equivalent |
|----------|------------------|
| `app/models/` | `<django_app>/models.py` |
| `app/api/` | `<django_app>/views.py` or `api.py` |
| `app/services/` | `<django_app>/services.py` (same pattern) |
| `app/tasks/` | `<django_app>/tasks.py` |
| `app/templates/` | `<django_app>/templates/<app_name>/` |
| `app/middleware/` | `<django_app>/middleware.py` |
| `app/core/config.py` | `settings.py` |
| `alembic/` | `<django_app>/migrations/` |
| `boilerplate/templates/` | Django reusable apps (`pip install django-xxx`) |
| `tests/` | `tests/` (Django uses same convention) |

---

## Common Pitfalls

### 1. UUID Primary Keys

Django's default is auto-incrementing integers. Polyglot uses UUIDs. Add to
your base model:

```python
import uuid

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Meta:
        abstract = True
```

### 2. Async vs Sync

FastAPI is fully async. Django views are synchronous by default (Django 4.1+
has experimental async support). For API views, DRF and Django Ninja handle
this transparently. For task code that's heavily async, Celery's async support
or Django Q are good options.

### 3. Session Management

Polyglot uses `starlette-session` with server-side session storage. Django
uses its own session framework. Map your session store (Redis, DB, etc.)
in Django's `SESSION_ENGINE` setting.

### 4. Auth Migration

If using OIDC, switch to `mozilla-django-oidc` or `django-allauth`.
The OIDC provider configuration (client ID, secret, endpoints) is
identical — only the integration code changes.

### 5. Database Migrations During Transition

During coexistence, run Alembic *or* Django migrations — never both.
Pick one as the source of truth. Using `--fake-initial` tells Django
the tables already exist.

---

## Why Polyglot Makes Migration Easier

The Polyglot architecture is deliberately aligned with Django patterns:

1. **Model-first architecture**: Both systems organize code around models.
   Your `app/models/` directory maps directly to Django app models.

2. **Service layer separation**: Polyglot services (`app/services/`,
   `app/components/*/service.py`) are plain Python classes. They port
   directly to Django with minimal changes.

3. **Task abstraction**: Procrastinate tasks use the same pattern as
   Celery tasks — decorated functions with a name. The `defer()` call
   becomes `.delay()` or `async_task()`.

4. **Component isolation**: Each Polyglot template is a self-contained
   module. These map cleanly to Django reusable apps or packages.

5. **Pydantic → DRF Serializer**: Both define input/output shapes with
   validation. The mental model transfers directly.

6. **Environment-driven configuration**: Both systems use env vars with
   sensible defaults. Your `.env` file remains largely unchanged.

7. **Postgres-native**: Both use Postgres as the primary datastore.
   No database migration needed — just point Django at the same DB.

### Migration Time Estimates

| Application Size | Estimated Time |
|-----------------|----------------|
| < 5 models, < 10 routes | 2-4 hours |
| 5-15 models, 10-30 routes | 1-2 days |
| 15-50 models, 30-100 routes | 3-5 days |
| 50+ models, 100+ routes | 1-2 weeks phased |

---

## Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Ninja](https://django-ninja.dev/)
- [django-import-export](https://django-import-export.readthedocs.io/)
- [Celery with Django](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
- [mozilla-django-oidc](https://mozilla-django-oidc.readthedocs.io/)
