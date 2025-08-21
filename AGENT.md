# AGENT.md

This file provides guidance to Code Agent like Claude Code and Gemini CLI when working with code in this repository.

## Project Overview

This is **nonebot-plugin-pixivbot**, a NoneBot plugin that provides Pixiv image sharing, artist update notifications, and scheduled content delivery for chat platforms. The plugin integrates with the Pixiv API to fetch illustrations, rankings, and user content.

## Development Commands

### Package Management
- **Install dependencies**: `pdm sync -d -G dev`
- **Install production dependencies**: `pdm sync`
- **Add new dependency**: `pdm add <package>`
- **Add dev dependency**: `pdm add -dG dev <package>`

### Testing
- **Run all tests**: `pdm run pytest tests`
- **Run tests with coverage**: `pdm run pytest --cov tests`
- **Run specific test file**: `pdm run pytest tests/test_specific.py`

### Code Quality
- **Lint code**: `pdm run flake8`
- **Auto-format code**: `pdm run autopep8 --in-place --recursive src/`

### Development Server
- **Run with bot.py**: `python bot.py` (requires proper NoneBot configuration)

## Architecture Overview

### Core Components

1. **Context System** (`context.py`, `global_context.py`):
   - Custom dependency injection container
   - Manages singleton instances and lazy loading
   - Central registry for services and repositories

2. **Handler System** (`handler/`):
   - **Command handlers** (`handler/command/`): Process bot commands like `/pixivbot schedule`
   - **Common handlers** (`handler/common/`): Handle natural language queries like "来张图"
   - **Interceptors** (`handler/interceptor/`): Middleware for permissions, loading prompts, retries
   - **Schedulers** (`handler/schedule/`): Background tasks for scheduled content
   - **Watchers** (`handler/watch/`): Monitor user/artist updates
   - **Sniffers** (`handler/sniffer/`): Detect Pixiv links and poke events

3. **Service Layer** (`service/`):
   - **PixivService**: Core Pixiv API integration
   - **Scheduler**: Manages timed content delivery
   - **Watchman**: Handles artist/user update monitoring
   - **Postman**: Message delivery service

4. **Data Layer** (`data/`):
   - **PixivRepo** (`data/pixiv_repo/`): Repository pattern for Pixiv data with local/remote separation
   - **Models** (`model/`): Data models for illustrations, users, subscriptions
   - **SQL migrations** (`data/source/sql/migration/`): Database schema versioning

5. **Configuration** (`config.py`):
   - Comprehensive configuration system using Pydantic
   - Supports SQLite/PostgreSQL databases
   - Caching, proxy, and feature toggle settings

### Key Patterns

- **Repository Pattern**: Abstract data access with local caching and remote API fallback
- **Interceptor Chain**: Request/response middleware for cross-cutting concerns
- **Context-based DI**: Manages dependencies without external framework
- **Lazy Loading**: Services initialized on-demand via context system

### Database Support
- **SQLite** (default): Uses aiosqlite driver
- **PostgreSQL**: Requires asyncpg (`pip install asyncpg`)
- **Migrations**: Automatic schema versioning in `data/source/sql/migration/`

### Pixiv Integration
- Uses `PixivPy-Async` library for API access
- Requires `refresh_token` for authentication
- Supports proxy configuration for network restrictions
- Implements comprehensive caching strategy

## Configuration Requirements

### Minimal Setup
```env
PIXIV_REFRESH_TOKEN=your_refresh_token_here
```

### Database Configuration
- SQLite: `PIXIV_SQL_CONN_URL=sqlite+aiosqlite:///path/to/db.db`
- PostgreSQL: `PIXIV_SQL_CONN_URL=postgresql+asyncpg://user:pass@host:port/db`

### Development Environment
Set up test environment in `src/tests/conftest.py` with test tokens and superuser configuration.

## Plugin Integration

This plugin integrates with multiple NoneBot ecosystem plugins:
- `nonebot-plugin-apscheduler`: Task scheduling
- `nonebot-plugin-access-control`: Permission management
- `nonebot-plugin-session`: User session management
- `nonebot-plugin-localstore`: Local file storage
- `nonebot-plugin-saa`: Cross-platform message sending

## Common Development Tasks

When adding new features:
1. Define models in `model/` if new data structures are needed
2. Implement repository methods in `data/pixiv_repo/` for data access
3. Create handlers in appropriate `handler/` subdirectory
4. Register services in `service/` and bind in context
5. Add configuration options to `config.py`
6. Write tests in `src/tests/`