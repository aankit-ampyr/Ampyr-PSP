# AmpyrOS Enterprise Platform
## Comprehensive Implementation Plan

---

## 1. Executive Summary

### 1.1 Vision Statement

**AmpyrOS** is the unified enterprise platform for **Ampyr Energy Tech Solution Pvt Ltd** that serves as the central hub for all internal tools, applications, and modules used across the organization.

### 1.2 Core Objectives

| Objective | Description |
|-----------|-------------|
| **Unified Access** | Single sign-on entry point for all Ampyr applications |
| **Centralized Control** | Role-based access management across all modules |
| **Modular Architecture** | Plug-and-play system for adding new tools |
| **Scalability** | Architecture that grows with organizational needs |
| **Security** | Enterprise-grade authentication and audit trails |

### 1.3 Platform Modules

| Module | Purpose | Status |
|--------|---------|--------|
| **BESS Sizing Tool** | Battery energy storage system optimization and sizing | Existing (to be integrated) |
| **RAG** | Hybrid Retrieval-Augmented Generation for document intelligence | Planned |
| **Asset Dashboard** | Real-time monitoring and analytics for energy assets | Planned |
| **Bid Forecasting** | Energy market bid optimization and forecasting | Planned |
| **Ampyr Intelligence** | AI/ML analytics and insights platform | Planned |
| **[Future Modules]** | Extensible architecture for new tools | TBD |

---

## 2. Platform Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AmpyrOS Platform                                │
│                     "One Platform, Multiple Solutions"                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                     PRESENTATION LAYER                             │     │
│   │   ┌─────────────────────────────────────────────────────────────┐ │     │
│   │   │              AmpyrOS Shell (Web Application)                 │ │     │
│   │   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │ │     │
│   │   │  │  BESS   │ │   RAG   │ │  Asset  │ │   Bid   │ │ Ampyr  │ │ │     │
│   │   │  │ Sizing  │ │         │ │Dashboard│ │Forecast │ │ Intel  │ │ │     │
│   │   │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘ │ │     │
│   │   └─────────────────────────────────────────────────────────────┘ │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                      │                                       │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                      PLATFORM SERVICES LAYER                       │     │
│   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │     │
│   │  │     Auth     │ │    Access    │ │    Module    │ │  Shared   │ │     │
│   │  │   Service    │ │   Control    │ │   Registry   │ │ Services  │ │     │
│   │  │    (SSO)     │ │   (RBAC)     │ │              │ │           │ │     │
│   │  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                      │                                       │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                         DATA LAYER                                 │     │
│   │     ┌────────────┐    ┌────────────┐    ┌────────────────┐        │     │
│   │     │ PostgreSQL │    │   Redis    │    │   S3/MinIO     │        │     │
│   │     │ (Database) │    │  (Cache)   │    │ (File Storage) │        │     │
│   │     └────────────┘    └────────────┘    └────────────────┘        │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Description

#### 2.2.1 AmpyrOS Shell
The main web application that serves as the entry point for all users:
- **Module Launcher**: Dashboard displaying available modules based on user permissions
- **Navigation**: Unified header and sidebar across all modules
- **User Profile**: Account settings, preferences, notifications
- **Admin Console**: User management, access control (for admins)

#### 2.2.2 Authentication Service
Centralized identity management:
- **SSO Integration**: Microsoft Entra ID or Google Workspace
- **Token Management**: JWT-based session handling
- **Session Control**: Login, logout, session timeout
- **Audit Logging**: All authentication events tracked

#### 2.2.3 Access Control (RBAC)
Fine-grained permission system:
- **Platform Roles**: Platform Admin, Standard User
- **Module Roles**: Each module defines its own roles (Admin, Engineer, Viewer, etc.)
- **Permission Grants**: Users assigned roles per module
- **Access Validation**: Middleware checks permissions on every request

#### 2.2.4 Module Registry
Dynamic module management:
- **Module Catalog**: List of all available modules
- **Manifest System**: Each module describes its capabilities
- **Activation Control**: Enable/disable modules per user or organization
- **Version Management**: Track module versions and updates

#### 2.2.5 Shared Services
Common utilities available to all modules:
- **File Storage**: Upload, download, manage files
- **Notifications**: In-app and email notifications
- **Audit Trail**: Activity logging across all modules
- **Configuration**: Centralized settings management

---

## 3. Authentication & Access Control

### 3.1 Authentication Flow

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   User   │────▶│ AmpyrOS      │────▶│  SSO Provider   │────▶│   AmpyrOS    │
│          │     │ Login Page   │     │ (Microsoft/     │     │   Dashboard  │
│          │     │              │     │  Google)        │     │              │
└──────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
                        │                      │                      │
                        │    1. Redirect       │                      │
                        │───────────────────▶  │                      │
                        │                      │                      │
                        │    2. Authenticate   │                      │
                        │                      │                      │
                        │    3. Token          │                      │
                        │◀───────────────────  │                      │
                        │                      │                      │
                        │    4. Create Session │                      │
                        │──────────────────────────────────────────▶  │
```

### 3.2 Role Hierarchy

```
Platform Level
├── Platform Admin
│   └── Full access to all modules and platform settings
│
└── Standard User
    └── Access only to assigned modules with assigned roles

Module Level (Example: BESS Sizing)
├── Module Admin
│   └── Full access within module + user management for module
├── Engineer
│   └── Create, edit, run simulations, export
└── Viewer
    └── Read-only access to shared projects
```

### 3.3 Permission Matrix

| Action | Platform Admin | Module Admin | Engineer | Viewer |
|--------|----------------|--------------|----------|--------|
| Access Platform Settings | ✅ | ❌ | ❌ | ❌ |
| Manage All Users | ✅ | ❌ | ❌ | ❌ |
| Manage Module Users | ✅ | ✅ | ❌ | ❌ |
| Create Projects | ✅ | ✅ | ✅ | ❌ |
| Edit Projects | ✅ | ✅ | ✅ (own) | ❌ |
| Run Simulations | ✅ | ✅ | ✅ | ❌ |
| View Results | ✅ | ✅ | ✅ | ✅ |
| Export Data | ✅ | ✅ | ✅ | ❌ |
| Delete Projects | ✅ | ✅ | ✅ (own) | ❌ |

---

## 4. Module System

### 4.1 Module Architecture

Each module is a self-contained application that integrates with AmpyrOS:

```
┌─────────────────────────────────────────────────────────────┐
│                        MODULE ANATOMY                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   module.yaml          ─── Module manifest (metadata)       │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                       SDK                            │   │
│   │   Pure business logic, no UI dependencies            │   │
│   │   • Core algorithms                                  │   │
│   │   • Data models                                      │   │
│   │   • Business rules                                   │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                       API                            │   │
│   │   REST endpoints for module functionality            │   │
│   │   • CRUD operations                                  │   │
│   │   • Business operations                              │   │
│   │   • Export endpoints                                 │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                        UI                            │   │
│   │   User interface components                          │   │
│   │   • Pages / Views                                    │   │
│   │   • Components                                       │   │
│   │   • Visualizations                                   │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                     Database                         │   │
│   │   Module-specific data storage                       │   │
│   │   • Models / Schemas                                 │   │
│   │   • Migrations                                       │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Module Manifest (module.yaml)

```yaml
# Example: Module Manifest Template
id: module-id
name: Module Name
version: 1.0.0
description: Module description
author: Ampyr Energy Tech
icon: icon-name
category: category-name

# Integration configuration
integration:
  type: embedded                    # embedded | iframe | external
  entry_point: /modules/module-id
  api_prefix: /api/v1/module-id
  ui_framework: streamlit           # streamlit | react | vue

# Module-specific roles
roles:
  - name: admin
    display_name: Administrator
    permissions: [create, read, update, delete, export, manage_users]
  - name: user
    display_name: User
    permissions: [create, read, update, export]
  - name: viewer
    display_name: Viewer
    permissions: [read]

# Dependencies on platform services
dependencies:
  - storage           # File upload/download
  - notifications     # Email/in-app notifications
  - audit             # Activity logging

# Resource configuration
resources:
  max_items_per_user: 100
  max_operations_per_day: 500
  max_file_size_mb: 50
```

### 4.3 Integration Patterns

#### Pattern 1: Embedded Module (Recommended)
- Module UI renders within AmpyrOS shell
- Shares header, sidebar, and navigation
- Full access to platform SDK
- Best for: New modules built for AmpyrOS

#### Pattern 2: Iframe Module
- Existing application embedded in iframe
- Token passed via URL or postMessage
- Limited platform integration
- Best for: Legacy applications

#### Pattern 3: External Link
- SSO redirect to external application
- Opens in new tab/window
- Minimal integration
- Best for: Third-party tools

---

## 5. Platform Database Schema

```sql
-- =============================================
-- PLATFORM CORE TABLES
-- =============================================

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    is_platform_admin BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Modules registry
CREATE TABLE modules (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(20) NOT NULL,
    icon VARCHAR(50),
    category VARCHAR(50),
    base_url VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    config JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Module roles
CREATE TABLE module_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id VARCHAR(50) REFERENCES modules(id) ON DELETE CASCADE,
    role_name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    permissions JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(module_id, role_name)
);

-- User module access
CREATE TABLE user_module_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    module_id VARCHAR(50) REFERENCES modules(id) ON DELETE CASCADE,
    role_id UUID REFERENCES module_roles(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, module_id)
);

-- Audit logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id UUID REFERENCES users(id),
    module_id VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT
);

-- Create indexes
CREATE INDEX idx_audit_user_timestamp ON audit_logs(user_id, timestamp DESC);
CREATE INDEX idx_audit_module_timestamp ON audit_logs(module_id, timestamp DESC);
CREATE INDEX idx_user_module_access_user ON user_module_access(user_id);
```

---

## 6. Platform APIs

### 6.1 Authentication APIs
```
POST   /api/v1/auth/login           # Initiate SSO login
GET    /api/v1/auth/callback        # SSO callback handler
POST   /api/v1/auth/logout          # Logout and invalidate session
GET    /api/v1/auth/me              # Get current user info
POST   /api/v1/auth/refresh         # Refresh access token
```

### 6.2 User Management APIs
```
GET    /api/v1/users                # List all users (admin)
POST   /api/v1/users                # Create user (admin)
GET    /api/v1/users/{id}           # Get user by ID
PUT    /api/v1/users/{id}           # Update user
DELETE /api/v1/users/{id}           # Deactivate user
```

### 6.3 Module Registry APIs
```
GET    /api/v1/modules              # List all modules
GET    /api/v1/modules/{id}         # Get module details
GET    /api/v1/modules/{id}/roles   # Get module roles
```

### 6.4 Access Management APIs
```
GET    /api/v1/access/users/{id}/modules    # Get user's module access
POST   /api/v1/access/grant                 # Grant module access
DELETE /api/v1/access/revoke                # Revoke module access
GET    /api/v1/access/modules/{id}/users    # Get module's users
```

---

## 7. Technology Stack

### 7.1 Recommended Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14 + TypeScript | Modern React framework, SSR support |
| **UI Components** | Tailwind CSS + shadcn/ui | Rapid development, consistent design |
| **Backend** | FastAPI (Python 3.13) | Async support, automatic API docs |
| **Database** | PostgreSQL 16 | Robust, JSONB support, RLS |
| **Cache** | Redis 7 | Session management, caching |
| **File Storage** | S3 / MinIO | Scalable object storage |
| **Auth** | Microsoft Entra ID | Enterprise SSO |
| **Containerization** | Docker + Docker Compose | Consistent deployments |
| **CI/CD** | GitHub Actions | Automated builds and deploys |

### 7.2 AmpyrOS SDK

```python
# ampyros/sdk/__init__.py
"""
AmpyrOS SDK - Shared utilities for module development
"""

from .auth import (
    get_current_user,
    require_permission,
    require_role,
    get_user_permissions,
)

from .storage import (
    upload_file,
    download_file,
    delete_file,
    get_signed_url,
)

from .notifications import (
    send_notification,
    send_email,
)

from .audit import (
    log_action,
    get_audit_trail,
)

from .config import (
    get_module_config,
    get_platform_config,
)
```

---

## 8. Deployment Architecture

### 8.1 Infrastructure Diagram

```
                            ┌─────────────────┐
                            │   Internet      │
                            └────────┬────────┘
                                     │
                            ┌────────▼────────┐
                            │ Load Balancer   │
                            │   (HTTPS/443)   │
                            └────────┬────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
     ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
     │    Frontend     │   │    Backend      │   │    Workers      │
     │   (Next.js)     │   │   (FastAPI)     │   │   (Celery)      │
     │   Port: 3000    │   │   Port: 8000    │   │                 │
     └────────┬────────┘   └────────┬────────┘   └────────┬────────┘
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
     ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
     │   PostgreSQL    │   │     Redis       │   │   MinIO (S3)    │
     │   Port: 5432    │   │   Port: 6379    │   │   Port: 9000    │
     └─────────────────┘   └─────────────────┘   └─────────────────┘
```

### 8.2 Docker Compose Configuration

```yaml
version: '3.8'

services:
  # Frontend (Next.js)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
      - NEXT_PUBLIC_SSO_PROVIDER=azure
    depends_on:
      - api

  # Backend API (FastAPI)
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://ampyros:password@db:5432/ampyros
      - REDIS_URL=redis://redis:6379/0
      - S3_ENDPOINT=http://minio:9000
      - AZURE_TENANT_ID=${AZURE_TENANT_ID}
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      - AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
    depends_on:
      - db
      - redis
      - minio

  # Background Workers
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A ampyros.worker worker -l info
    environment:
      - DATABASE_URL=postgresql://ampyros:password@db:5432/ampyros
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - api
      - redis

  # PostgreSQL Database
  db:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=ampyros
      - POSTGRES_USER=ampyros
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # MinIO (S3-compatible storage)
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
```

---

## 9. Implementation Timeline

### 9.1 Timeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IMPLEMENTATION TIMELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Week 1-2: Platform Foundation                                              │
│  ├── Database schema setup                                                  │
│  ├── SSO authentication integration                                         │
│  └── Basic user management                                                  │
│                                                                              │
│  Week 3: Platform Core Services                                             │
│  ├── Access control (RBAC)                                                  │
│  ├── Module registry                                                        │
│  └── Audit logging                                                          │
│                                                                              │
│  Week 4: Platform UI                                                        │
│  ├── Shell application (Next.js)                                            │
│  ├── Module launcher dashboard                                              │
│  └── Admin console                                                          │
│                                                                              │
│  Week 5-6: First Module Integration (BESS Sizing)                           │
│  ├── SDK extraction                                                         │
│  ├── Database models                                                        │
│  ├── API endpoints                                                          │
│  └── UI integration                                                         │
│                                                                              │
│  Week 7: Deployment & Documentation                                         │
│  ├── Docker configuration                                                   │
│  ├── CI/CD pipeline                                                         │
│  └── User documentation                                                     │
│                                                                              │
│  Week 8+: Additional Modules                                                │
│  ├── RAG integration                                                        │
│  ├── Asset Dashboard                                                        │
│  └── Other modules                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Phase Details

#### Phase 1: Platform Foundation (Week 1-2)
- PostgreSQL database with platform schema
- SSO integration (Microsoft Entra ID)
- User authentication flow
- Basic session management

#### Phase 2: Platform Core (Week 3)
- RBAC system
- Module registry
- Audit logging
- AmpyrOS SDK v1

#### Phase 3: Platform UI (Week 4)
- Next.js shell application
- Module launcher
- Admin console
- User settings

#### Phase 4: Deployment (Week 7)
- Docker configuration
- CI/CD pipeline
- Documentation

---

## 10. Success Criteria

### 10.1 Platform Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Login Success Rate | > 99% | Auth logs |
| Page Load Time | < 3 seconds | Performance monitoring |
| API Response Time | < 500ms | API metrics |
| Uptime | > 99.9% | Health checks |
| User Adoption | 100% of target users | Active user count |

### 10.2 Verification Checklist

- [ ] SSO login works with corporate credentials
- [ ] Users see only modules they have access to
- [ ] Platform admins can manage users
- [ ] Audit logs capture all actions
- [ ] Module launcher displays correctly
- [ ] Auth persists across modules
- [ ] Switching modules works smoothly

---

## 11. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| SSO integration delays | High | Medium | Start early, have fallback |
| Performance issues | Medium | Low | Load testing, caching |
| Data migration errors | High | Low | Thorough testing, backups |
| User adoption resistance | Medium | Medium | Training, documentation |
| Scope creep | High | Medium | Strict change control |

---

## 12. Next Steps

1. **Immediate**: Finalize SSO provider choice (Microsoft Entra vs Google)
2. **Week 1**: Set up development environment and database
3. **Week 2**: Complete authentication integration
4. **Week 3**: Begin first module integration
5. **Ongoing**: Weekly progress reviews
