## Architecture Standards

### File Size & Structure

* **Max file size: 200-250 lines**
* Break any file exceeding the limit into smaller modules
* Organize modules into directories by feature/domain
* Favor **composition** and modular design

### Design Philosophy

> Build simple, maintainable systems that solve current needs

#### Required Principles

* **KISS** - Keep It Simple
* **YAGNI** - Only build what is currently required
* **SOLID** principles:

  * Single Responsibility
  * Open/Closed
  * Liskov Substitution
  * Interface Segregation
  * Dependency Inversion

---

## Expected Output Style

* Clean, readable, documented code
* Clear separation of **data**, **logic**, and **configuration**
* Self-explanatory names
* Single-responsibility functions
* Minimalistic, focused architecture

---

## Avoid

* Over-engineering or futuristic abstractions
* Monolithic / god scripts
* Added features without request
* Deep inheritance - prefer composition

---
