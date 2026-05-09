# PyQt Desktop Application Engineering Skill

## Goal

Build maintainable, scalable, industrial-grade PyQt/PySide desktop applications.

The architecture should prioritize:

* clear separation of UI and business logic
* long-term maintainability
* extensibility
* plugin capability
* thread safety
* testability
* predictable state management

The project structure and design philosophy should resemble mature desktop applications such as:

* Anki
* qutebrowser
* calibre
* Spyder

---

# Core Principles

## 1. UI is NOT business logic

Never place business logic directly inside:

* QWidget
* QMainWindow
* Dialog classes
* button click handlers

UI components should only:

* display state
* collect user input
* dispatch actions

All business logic must live in:

* services
* managers
* domain models
* workers

Bad:

```python
button.clicked.connect(
    lambda: sqlite.execute(...)
)
```

Good:

```python
button.clicked.connect(self.on_add_word)

def on_add_word(self):
    self.word_service.add_word(...)
```

---

## 2. Separate application layers

Use layered architecture.

Recommended dependency direction:

```text
UI
 ↓
Controllers / Actions
 ↓
Services
 ↓
Repositories / Database
 ↓
Infrastructure
```

UI must never directly manipulate database state.

---

## 3. Prefer composition over giant windows

Avoid monolithic QMainWindow classes with thousands of lines.

Instead:

* split features into widgets
* use reusable components
* isolate dialogs
* isolate panels
* isolate toolbars

---

## 4. Use Qt signal/slot as event system

Use signals for decoupling.

Avoid directly invoking unrelated widgets.

Bad:

```python
main_window.sidebar.refresh()
```

Good:

```python
word_added.emit(word)
```

---

## 5. GUI thread must stay responsive

Never block GUI thread.

Forbidden in GUI thread:

* time.sleep
* heavy OCR
* network requests
* database indexing
* AI inference
* file scanning

Use:

* QThread
* QRunnable
* QThreadPool

Pattern:

```text
GUI Thread
    ↓
Worker Thread
    ↓
Signal Result Back
```

---

# Recommended Project Structure

```text
app/
│
├── main.py
├── bootstrap/
│
├── ui/
│   ├── windows/
│   ├── dialogs/
│   ├── widgets/
│   ├── views/
│   ├── styles/
│   └── resources/
│
├── domain/
│   ├── models/
│   ├── entities/
│   ├── value_objects/
│   └── enums/
│
├── services/
│   ├── study_service.py
│   ├── audio_service.py
│   └── sync_service.py
│
├── repositories/
│   ├── word_repository.py
│   └── review_repository.py
│
├── workers/
│   ├── ocr_worker.py
│   ├── sync_worker.py
│   └── audio_worker.py
│
├── database/
│   ├── connection.py
│   ├── migrations/
│   └── schema/
│
├── plugins/
│
├── config/
│
├── utils/
│
├── tests/
│
└── assets/
```

---

# Naming Conventions

## File naming

Use snake_case.

Examples:

```text
word_service.py
review_scheduler.py
main_window.py
```

Avoid:

```text
WordService.py
MainWindow.py
```

---

## Class naming

Use PascalCase.

Examples:

```python
class MainWindow
class ReviewScheduler
class WordRepository
```

---

## Signal naming

Signals should describe events.

Good:

```python
word_added
review_completed
sync_finished
```

Bad:

```python
do_update
refresh_now
```

---

## Widget naming

Widget classes should end with:

* Widget
* Dialog
* View
* Window

Examples:

```python
ReviewWidget
SettingsDialog
DeckView
MainWindow
```

---

# UI Guidelines

## 1. Keep widgets small

A widget should ideally:

* manage one responsibility
* remain under ~300 lines where possible

Split large widgets aggressively.

---

## 2. Prefer layouts over absolute positioning

Use:

* QVBoxLayout
* QHBoxLayout
* QGridLayout

Avoid hardcoded geometry.

---

## 3. Avoid excessive Designer dependence

Qt Designer is acceptable for:

* rapid prototyping
* simple forms

Complex widgets should be built in Python code.

---

## 4. Use centralized styles

Avoid inline styling.

Use:

* QSS files
* theme manager
* style constants

---

# Database Design

## 1. Use repository abstraction

UI and services should never execute raw SQL directly.

Bad:

```python
cursor.execute(...)
```

Good:

```python
word_repository.add(...)
```

---

## 2. Domain models are important

Design models carefully.

Example:

```text
Word
Sentence
ReviewRecord
Deck
Tag
AudioAsset
```

Avoid generic structures like:

```text
Item
Data
Info
```

---

# State Management

## 1. Single source of truth

Avoid duplicated mutable state across widgets.

Use:

* centralized services
* models
* signals

---

## 2. Avoid hidden side effects

Methods should be predictable.

Bad:

```python
refresh_ui()
```

that secretly writes database state.

---

# Plugin System

Design for extensibility early.

Plugins should:

* register actions
* register menu items
* register hooks
* avoid modifying core logic directly

Prefer hook/event systems over monkey patching.

---

# Logging

Use structured logging.

Recommended:

```python
from loguru import logger
```

Log:

* worker failures
* sync failures
* plugin loading
* database migrations

Avoid excessive print().

---

# Error Handling

Never silently ignore exceptions.

Bad:

```python
try:
    ...
except:
    pass
```

Good:

```python
except Exception as e:
    logger.exception(e)
```

---

# Recommended Technologies

## GUI

* PySide6 preferred
* PyQt acceptable

## Database

* SQLite
* SQLAlchemy optional

## Logging

* loguru

## Networking

* httpx

## Packaging

* Nuitka preferred
* PyInstaller acceptable

---

# Build Philosophy

The application should support:

* clean packaging
* reproducible builds
* portable deployment
* resource versioning
* plugin loading

Recommended structure:

```text
scripts/
    build.py
    package.py
    release.py
```

---

# Testing Philosophy

Test:

* services
* repositories
* schedulers
* parsers

Do NOT focus only on GUI tests.

Business logic should be testable independently of UI.

---

# Architecture Goals

The application should remain maintainable when:

* features double
* plugins increase
* data grows
* threads increase
* AI/OCR features are added

Prioritize:

* clarity
* decoupling
* modularity
* extensibility

over short-term speed.
