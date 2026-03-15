# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for MediGuard AI. ADRs capture important architectural decisions along with their context and consequences.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](./001-multi-agent-architecture.md) | Multi-Agent Architecture | Accepted | 2024-01-15 |
| [ADR-002](./002-opensearch-vector-store.md) | OpenSearch as Vector Store | Accepted | 2024-01-16 |
| [ADR-003](./003-fastapi-async-framework.md) | FastAPI for Async API Layer | Accepted | 2024-01-17 |
| [ADR-004](./004-redis-caching-strategy.md) | Redis Multi-Level Caching | Accepted | 2024-01-18 |
| [ADR-005](./005-langfuse-observability.md) | Langfuse for LLM Observability | Accepted | 2024-01-19 |
| [ADR-006](./006-docker-containerization.md) | Docker Multi-Stage Builds | Accepted | 2024-01-20 |
| [ADR-007](./007-rate-limiting-approach.md) | Token Bucket Rate Limiting | Accepted | 2024-01-21 |
| [ADR-008](./008-feature-flags-system.md) | Dynamic Feature Flags | Accepted | 2024-01-22 |
| [ADR-009](./009-distributed-tracing.md) | OpenTelemetry Distributed Tracing | Accepted | 2024-01-23 |
| [ADR-010](./010-security-compliance.md) | HIPAA Compliance Strategy | Accepted | 2024-01-24 |

## ADR Template

```markdown
# ADR-XXX: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[What is the issue that we're seeing that is motivating this decision?]

## Decision
[What is the change that we're proposing and/or doing?]

## Consequences
[What becomes easier or more difficult to do because of this change?]

## Implementation
[How will this be implemented?]

## Notes
[Any additional notes or references]
```

## How to Add a New ADR

1. Copy the template to a new file: `cp template.md XXX-decision-name.md`
2. Replace placeholders with actual content
3. Update the index in this README
4. Submit as a pull request for review
