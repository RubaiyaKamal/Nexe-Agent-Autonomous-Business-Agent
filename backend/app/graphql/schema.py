import uuid
from typing import Optional

import strawberry
from fastapi import Depends
from strawberry.fastapi import GraphQLRouter

from app.database import get_session
from app.graphql.resolvers.log_resolvers import (
    resolve_log_entry,
    resolve_logs,
    resolve_reasoning_traces,
    resolve_run_audit_summary,
)
from app.graphql.types import LogEntryType, LogFilterInput, ReasoningTraceType, RunAuditSummaryType
from app.middleware.auth import require_current_user


@strawberry.type
class Query:
    @strawberry.field
    async def logs(self, filter: LogFilterInput, info: strawberry.types.Info) -> list[LogEntryType]:
        return await resolve_logs(filter, info)

    @strawberry.field
    async def log_entry(self, id: uuid.UUID, info: strawberry.types.Info) -> Optional[LogEntryType]:
        return await resolve_log_entry(id, info)

    @strawberry.field
    async def reasoning_traces(
        self,
        run_id: uuid.UUID,
        task_id: Optional[uuid.UUID],
        info: strawberry.types.Info,
    ) -> list[ReasoningTraceType]:
        return await resolve_reasoning_traces(run_id, task_id, info)

    @strawberry.field
    async def run_audit_summary(self, run_id: uuid.UUID, info: strawberry.types.Info) -> RunAuditSummaryType:
        return await resolve_run_audit_summary(run_id, info)


schema = strawberry.Schema(query=Query)


async def get_graphql_context(
    db=Depends(get_session),
    current_user: dict = Depends(require_current_user),
):
    return {"db": db, "user": current_user}


graphql_router = GraphQLRouter(schema, context_getter=get_graphql_context)
