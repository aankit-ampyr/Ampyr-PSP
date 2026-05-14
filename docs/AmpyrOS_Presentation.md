# AmpyrOS Platform - Presentation Slides

## How to Use This Document

This document contains slide-by-slide content for creating a PowerPoint presentation. Each section represents one slide with:

- **Title**: The slide heading
- **Content**: Key points and visuals (represented as ASCII diagrams)
- **Speaker Notes**: Talking points for the presenter

---

## Slide 1: Title Slide

### Content

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│                         AmpyrOS                              │
│                                                              │
│         Unified Enterprise Platform for Ampyr Group         │
│                                                              │
│                    Implementation Plan                       │
│                                                              │
│                        [Ampyr Logo]                          │
│                                                              │
│                     [Date] | [Presenter]                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Speaker Notes

- Welcome everyone to the AmpyrOS platform presentation
- This presentation covers our vision for a unified enterprise platform
- We'll discuss architecture, modules, timeline, and next steps

---

## Slide 2: Agenda

### Content

```
AGENDA

1. Executive Summary

2. Platform Vision & Architecture

3. Module Overview

4. Key Features

5. Implementation Roadmap

6. Technology Stack

7. Next Steps & Discussion
```

### Speaker Notes

- Quick overview of what we'll cover today
- Feel free to ask questions at any point
- We'll have dedicated Q&A time at the end

---

## Slide 3: Executive Summary - The Challenge

### Content

```
THE CHALLENGE

Current State:
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│  BESS   │  │   RAG   │  │  Asset  │  │   Bid   │
│ Sizing  │  │         │  │Dashboard│  │Forecast │
└────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘
     │            │            │            │
   Login        Login        Login        Login

• Multiple standalone applications
• Separate logins for each tool
• No unified user management
• Fragmented experience
• Difficult to manage access
```

### Speaker Notes

- Currently we have multiple standalone tools
- Each requires separate authentication
- No central place to manage who has access to what
- Users need to remember multiple URLs and credentials
- IT has no visibility into usage across tools

---

## Slide 4: Executive Summary - The Solution

### Content

```
THE SOLUTION: AmpyrOS

┌─────────────────────────────────────────────────────┐
│                      AmpyrOS                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │  BESS   │ │   RAG   │ │  Asset  │ │   Bid   │   │
│  │ Sizing  │ │         │ │Dashboard│ │Forecast │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                      │                               │
│              Single Sign-On                          │
│                      │                               │
│              Centralized Access                      │
└─────────────────────────────────────────────────────┘

KEY BENEFITS:
✓ One login for all applications
✓ Centralized user management
✓ Role-based access control
✓ Unified user experience
✓ Scalable for future tools
```

### Speaker Notes

- AmpyrOS is our solution - a unified platform
- One login provides access to all authorized tools
- Central place for admins to manage users and permissions
- Consistent experience across all modules
- Built to grow with the organization

---

## Slide 5: Platform Vision

### Content

```
"One Platform, Multiple Solutions"

┌───────────────────────────────────────────────────────────┐
│                        AmpyrOS                             │
│                                                            │
│   🔋 BESS Sizing    │   Battery storage optimization      │
│   ─────────────────────────────────────────────────────   │
│   📚 RAG            │   Document intelligence             │
│   ─────────────────────────────────────────────────────   │
│   📊 Asset Dashboard│   Real-time monitoring              │
│   ─────────────────────────────────────────────────────   │
│   📈 Bid Forecasting│   Market optimization               │
│   ─────────────────────────────────────────────────────   │
│   🧠 Ampyr Intel    │   AI analytics                      │
│   ─────────────────────────────────────────────────────   │
│   ➕ Future Modules │   Extensible architecture           │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

### Speaker Notes

- Our vision: One platform that houses all Ampyr tools
- Starting with BESS Sizing (already built)
- Adding RAG, Asset Dashboard, Bid Forecasting, Ampyr Intelligence
- Architecture designed to easily add more modules in the future
- Each module can have its own role structure

---

## Slide 6: Platform Architecture

### Content

```
PLATFORM ARCHITECTURE

┌─────────────────────────────────────────────────────┐
│              AmpyrOS Shell (UI)                      │
│     Module Launcher | Navigation | User Profile     │
└─────────────────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────┐
│              Platform Services                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │   Auth   │  │  Access  │  │  Module  │          │
│  │  (SSO)   │  │ Control  │  │ Registry │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────┐
│               Data Layer                             │
│     PostgreSQL  |  Redis  |  S3/MinIO               │
└─────────────────────────────────────────────────────┘
```

### Speaker Notes

- Three-layer architecture for clean separation
- Shell: What users see - module launcher, navigation
- Services: Auth, access control, module management
- Data: Databases for persistence, cache for speed, storage for files
- Each module plugs into this structure

---

## Slide 7: Authentication & SSO

### Content

```
SINGLE SIGN-ON (SSO)

    ┌─────────┐          ┌─────────────┐          ┌─────────┐
    │  User   │ ──────▶  │   AmpyrOS   │ ──────▶  │   SSO   │
    │         │          │   Login     │          │Provider │
    └─────────┘          └─────────────┘          └─────────┘
         │                                              │
         │              ┌─────────────┐                │
         └─────────────▶│  Dashboard  │◀───────────────┘
                        └─────────────┘

SUPPORTED PROVIDERS:
• Microsoft Entra ID (Azure AD)
• Google Workspace

FEATURES:
• Use existing corporate credentials
• No new passwords to remember
• Automatic user provisioning
• Session management
```

### Speaker Notes

- SSO means users log in with their existing corporate accounts
- We support Microsoft and Google identity providers
- No need to create or manage new passwords
- Users automatically get access based on their corporate identity
- Sessions are managed centrally

---

## Slide 8: Role-Based Access Control

### Content

```
ROLE-BASED ACCESS CONTROL (RBAC)

PLATFORM LEVEL:
┌─────────────────────────────────────────────────────┐
│ Platform Admin    │ Full access to all modules      │
│ Standard User     │ Access only to assigned modules │
└─────────────────────────────────────────────────────┘

MODULE LEVEL (Example: BESS Sizing):
┌─────────────────────────────────────────────────────┐
│ Admin      │ All permissions + user management      │
│ Engineer   │ Create, edit, run, export             │
│ Viewer     │ Read-only access                      │
└─────────────────────────────────────────────────────┘

• Each module defines its own roles
• Users can have different roles in different modules
• Permissions enforced at every level
```

### Speaker Notes

- Two-level permission system
- Platform level: Admin vs regular users
- Module level: Each module defines its own roles
- A user might be Admin in BESS Sizing but Viewer in Asset Dashboard
- This gives fine-grained control over who can do what

---

## Slide 9: User Experience - Module Launcher

### Content

```
MODULE LAUNCHER (Dashboard)

┌───────────────────────────────────────────────────────┐
│  AmpyrOS                              [User] ▼  [⚙️]   │
├───────────────────────────────────────────────────────┤
│                                                        │
│  Welcome, Ankit!                                      │
│                                                        │
│  Your Modules:                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │🔋 BESS   │ │📚 RAG    │ │📊 Asset  │ │📈 Bid    │ │
│  │ Sizing   │ │          │ │Dashboard │ │Forecast  │ │
│  │ [Open]   │ │ [Open]   │ │ [Open]   │ │ [Open]   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│                                                        │
│  Recent Activity:                                     │
│  • BESS Sizing: Project "Alpha" updated 2h ago       │
│  • Asset Dashboard: New alert on Inverter #12        │
│                                                        │
└───────────────────────────────────────────────────────┘
```

### Speaker Notes

- This is what users see after logging in
- Clean, simple interface showing available modules
- Only shows modules the user has access to
- Recent activity helps users pick up where they left off
- One click to launch any module

---

## Slide 10: BESS Sizing Module - Current vs Target

### Content

```
BESS SIZING MODULE

CURRENT STATE                    TARGET STATE
┌───────────────────┐           ┌───────────────────┐
│ Standalone App    │   ───▶    │ AmpyrOS Module    │
│ No persistence    │           │ Database storage  │
│ Single user       │           │ Multi-user        │
│ No access control │           │ Role-based access │
└───────────────────┘           └───────────────────┘

PRESERVED FEATURES:            ENHANCEMENTS:
✓ 5-step wizard                ✓ Save/load projects
✓ 7 dispatch templates         ✓ Team collaboration
✓ 8760-hour simulation         ✓ Version history
✓ 20-year projections          ✓ Shared solar profiles
✓ Export capabilities          ✓ Audit trail
```

### Speaker Notes

- BESS Sizing is our first module to integrate
- Currently standalone - all your work is lost when you close it
- After integration: save projects, share with team, track history
- All the core functionality remains the same
- We're adding persistence and collaboration, not changing the tool

---

## Slide 11: Implementation Timeline

### Content

```
IMPLEMENTATION TIMELINE

Week    1    2    3    4    5    6    7    8+
────────┴────┴────┴────┴────┴────┴────┴────┴────────

├──────────────────┐
│ PLATFORM CORE    │
│ • Database       │
│ • SSO Auth       │
│ • Access Control │
└──────────────────┘
              │
              ├──────────┐
              │ PLATFORM │
              │ UI       │
              └──────────┘
                        │
                        ├──────────────────┐
                        │ BESS MODULE      │
                        │ INTEGRATION      │
                        └──────────────────┘
                                          │
                                          ├───────────────
                                          │ DEPLOYMENT
                                          │ + ADDITIONAL
                                          │ MODULES
                                          └───────────────
```

### Speaker Notes

- 7-week implementation timeline
- Weeks 1-2: Build the foundation (database, authentication)
- Week 3: Core services (access control, module registry)
- Week 4: Platform UI (launcher, admin console)
- Weeks 5-6: Integrate BESS Sizing module
- Week 7: Deployment and documentation
- After Week 7: Add more modules

---

## Slide 12: Technology Stack

### Content

```
TECHNOLOGY STACK

FRONTEND                         BACKEND
┌───────────────────┐           ┌───────────────────┐
│ Next.js 14        │           │ FastAPI           │
│ TypeScript        │           │ Python 3.13       │
│ Tailwind CSS      │           │ Celery (workers)  │
└───────────────────┘           └───────────────────┘

DATABASE                         INFRASTRUCTURE
┌───────────────────┐           ┌───────────────────┐
│ PostgreSQL 16     │           │ Docker            │
│ Redis 7           │           │ Docker Compose    │
│ S3/MinIO          │           │ GitHub Actions    │
└───────────────────┘           └───────────────────┘

AUTHENTICATION
┌─────────────────────────────────────────────────────┐
│ Microsoft Entra ID (Azure AD) / Google Workspace    │
└─────────────────────────────────────────────────────┘
```

### Speaker Notes

- Modern, proven technology stack
- Frontend: Next.js for fast, SEO-friendly UI
- Backend: FastAPI (Python) - matches our existing BESS code
- Database: PostgreSQL for reliability
- Redis for caching and sessions
- Docker for consistent deployments
- Enterprise SSO via Microsoft or Google

---

## Slide 13: Benefits Summary

### Content

```
BENEFITS SUMMARY

FOR USERS
┌─────────────────────────────────────────────────────┐
│ ✓ Single login for all applications                 │
│ ✓ Unified, consistent experience                    │
│ ✓ Easy discovery of available tools                 │
│ ✓ Saved work and collaboration                      │
└─────────────────────────────────────────────────────┘

FOR ADMINISTRATORS
┌─────────────────────────────────────────────────────┐
│ ✓ Centralized user management                       │
│ ✓ Fine-grained access control                       │
│ ✓ Complete audit trail                              │
│ ✓ Easy onboarding/offboarding                       │
└─────────────────────────────────────────────────────┘

FOR ORGANIZATION
┌─────────────────────────────────────────────────────┐
│ ✓ Scalable platform for future tools                │
│ ✓ Reduced development overhead                      │
│ ✓ Improved security posture                         │
│ ✓ Better resource utilization                       │
└─────────────────────────────────────────────────────┘
```

### Speaker Notes

- Benefits for everyone in the organization
- Users: Simpler experience, save their work
- Admins: Control and visibility
- Organization: Efficiency, security, scalability
- This is an investment that pays off as we add more modules

---

## Slide 14: Next Steps

### Content

```
NEXT STEPS

IMMEDIATE (This Week)
┌─────────────────────────────────────────────────────┐
│ □ Finalize SSO provider (Microsoft Entra/Google)    │
│ □ Set up development environment                    │
│ □ Create project repository                         │
└─────────────────────────────────────────────────────┘

SHORT-TERM (Week 1-2)
┌─────────────────────────────────────────────────────┐
│ □ Database setup and schema creation                │
│ □ SSO authentication integration                    │
│ □ Basic platform shell                              │
└─────────────────────────────────────────────────────┘

MEDIUM-TERM (Week 3-6)
┌─────────────────────────────────────────────────────┐
│ □ Complete platform core                            │
│ □ BESS Sizing module integration                    │
│ □ Initial deployment                                │
└─────────────────────────────────────────────────────┘

DECISIONS NEEDED:
• SSO provider preference
• Deployment environment (cloud provider)
• Priority order for additional modules
```

### Speaker Notes

- Clear next steps with specific milestones
- Need decision on SSO provider this week
- Development starts immediately after
- BESS Sizing available by Week 6
- Would like input on module priority

---

## Slide 15: Q&A

### Content

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│                                                              │
│                                                              │
│                    QUESTIONS &                               │
│                    DISCUSSION                                │
│                                                              │
│                                                              │
│                                                              │
│                                                              │
│                    Thank you!                                │
│                                                              │
│                    [Contact Information]                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Speaker Notes

- Open floor for questions
- Topics to address if not asked:
  - Timeline flexibility
  - Resource requirements
  - Impact on existing workflows
  - Training needs
  - Support during transition

---

## Appendix Slide: Detailed Phase Breakdown

### Content

```
DETAILED PHASE BREAKDOWN

PHASE 1: Platform Foundation (Week 1-2)
• PostgreSQL database setup
• SSO authentication integration
• User management APIs
• Session management with Redis

PHASE 2: Platform Core (Week 3)
• Role-based access control (RBAC)
• Module registry system
• Audit logging
• AmpyrOS SDK for modules

PHASE 3: Platform UI (Week 4)
• Next.js shell application
• Module launcher dashboard
• Admin console for user management
• User settings and preferences

PHASE 4: BESS Integration (Week 5-6)
• Extract business logic to SDK
• Create API endpoints
• Database persistence
• UI integration with auth

PHASE 5: Deployment (Week 7)
• Docker containerization
• CI/CD pipeline
• Documentation
• User training
```

### Speaker Notes

- Detailed breakdown for those who want more specifics
- Each phase has clear deliverables
- We can adjust timeline based on priorities
- Documentation and training included

---

## Design Recommendations for PowerPoint

### Color Scheme

- Primary: Use Ampyr brand colors
- Secondary: Neutral grays
- Accent: Green for success, Blue for information

### Fonts

- Headings: Inter Bold or Roboto Bold
- Body: Inter Regular or Roboto Regular
- Monospace: JetBrains Mono (for code/technical content)

### Icons

- Use consistent icon set (Lucide, Heroicons, or Font Awesome)
- Module icons should be distinctive and memorable

### Layout Tips

- Keep slides clean with plenty of white space
- Use animations sparingly (fade in for bullet points)
- Include slide numbers
- Add Ampyr logo in footer

### Diagrams

- Recreate ASCII diagrams as proper graphics
- Use consistent colors and styling
- Add subtle shadows and gradients for depth

---

## Anticipated Questions

### Q: "How long until we can use it?"

**A:** BESS Sizing module will be available within AmpyrOS by Week 6-7. Other modules will follow based on priority.

### Q: "What about our existing BESS Sizing work?"

**A:** Current work is in session state, so it would need to be recreated. We can help migrate any critical configurations.

### Q: "Can we add more modules later?"

**A:** Yes, the architecture is specifically designed for easy module addition. Each new module follows the same integration pattern.

### Q: "What about mobile access?"

**A:** The platform is responsive and works on tablets. A dedicated mobile app could be added in the future if needed.

### Q: "Who will maintain this?"

**A:** The platform will be maintained by the internal development team, with documentation for operations.

### Q: "What happens if SSO is down?"

**A:** SSO providers (Microsoft, Google) have 99.99% uptime SLAs. We can add fallback authentication if required.

### Q: "How is data secured?"

**A:** All data is encrypted at rest and in transit. Access is controlled via RBAC. Full audit logging tracks all actions.
