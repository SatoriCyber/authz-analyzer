import re
from dataclasses import dataclass
from logging import Logger
from typing import Dict, Generator, List, Optional, Set

from aws_ptrp.iam.policy.policy_document import PolicyDocument
from aws_ptrp.iam.policy.policy_document_utils import fix_stmt_regex_to_valid_regex
from aws_ptrp.principals import Principal
from aws_ptrp.ptrp_allowed_lines.allowed_line_nodes_base import PathFederatedPrincipalNodeBase
from aws_ptrp.ptrp_models.ptrp_model import AwsPtrpPathNodeType
from aws_ptrp.services import (
    ResolvedActionsSingleStmt,
    ResolvedSingleStmt,
    ResolvedSingleStmtGetter,
    ServiceActionBase,
    ServiceResourceBase,
    ServiceResourcesResolverBase,
    StmtResourcesToResolveCtx,
)
from aws_ptrp.services.federated_user.federated_user_actions import FederatedUserAction
from serde import field, serde


@serde
@dataclass
class FederatedUserPrincipal(PathFederatedPrincipalNodeBase, ServiceResourceBase):
    federated_principal: Principal = field(
        deserializer=Principal.from_policy_principal_str,
        serializer=Principal.to_policy_principal_str,
    )

    def __repr__(self):
        return self.get_node_arn()

    def __eq__(self, other):
        return self.get_node_arn() == other.get_node_arn()

    def __hash__(self):
        return hash(self.get_node_arn())

    # impl ServiceResourceBase
    def get_resource_arn(self) -> str:
        return self.federated_principal.get_arn()

    def get_resource_name(self) -> str:
        return self.federated_principal.get_name()

    def get_resource_policy(self) -> Optional[PolicyDocument]:
        return None

    def get_resource_account_id(self) -> str:
        assert self.federated_principal.is_federated_user_principal()
        account_id: Optional[str] = self.federated_principal.get_account_id()
        # principal from type federated user must have account-id
        assert account_id is not None
        return account_id

    # impl PathFederatedPrincipalNodeBase
    def get_service_resource(self) -> ServiceResourceBase:
        return self

    # impl NodeBase
    def get_node_name(self) -> str:
        return self.get_stmt_principal().get_name()

    def get_node_arn(self) -> str:
        return self.get_stmt_principal().get_arn()

    # impl PathNodeBase
    def get_path_type(self) -> AwsPtrpPathNodeType:
        return AwsPtrpPathNodeType.FEDERATED_USER

    # impl PrincipalNodeBase
    def get_stmt_principal(self) -> Principal:
        return self.federated_principal


@dataclass
class ResolvedFederatedUserActions(ResolvedActionsSingleStmt):
    actions: Set[FederatedUserAction]

    @property
    def resolved_stmt_actions(self) -> Set[ServiceActionBase]:
        return self.actions  # type: ignore[return-value]

    def add(self, actions: Set[FederatedUserAction]):
        self.actions = self.actions.union(actions)

    @classmethod
    def load(
        cls,
        actions: Set[FederatedUserAction],
    ) -> 'ResolvedFederatedUserActions':
        return cls(actions=actions.copy())


@dataclass
class FederatedUserResolvedStmt(ResolvedSingleStmtGetter):
    resolved_stmt: ResolvedSingleStmt

    def get(self) -> ResolvedSingleStmt:
        return self.resolved_stmt


@dataclass
class FederatedUserServiceResourcesResolver(ServiceResourcesResolverBase):
    resolved_stmts: List[FederatedUserResolvedStmt]

    def get_resolved_stmts(self) -> List[ResolvedSingleStmtGetter]:
        return self.resolved_stmts  # type: ignore[return-value]

    def is_principal_allowed_to_assume_federated_user(
        self, federated_user: FederatedUserPrincipal, principal: Principal
    ) -> bool:
        resolved_actions: Optional[Set[ServiceActionBase]] = self.get_resolved_actions_per_resource_and_principal(
            federated_user, principal
        )
        if not resolved_actions:
            return False
        for resolved_action in resolved_actions:
            if isinstance(resolved_action, FederatedUserAction) and resolved_action.is_get_federated_token_action():
                return True
        return False

    @staticmethod
    def _yield_resolve_resources_from_stmt_relative_id_regex(
        stmt_relative_id_regex: str,
        service_resources: Set[ServiceResourceBase],
    ) -> Generator[FederatedUserPrincipal, None, None]:
        regex = re.compile(fix_stmt_regex_to_valid_regex(stmt_relative_id_regex, with_case_sensitive=True))
        for service_resource in service_resources:
            # not using the regex match fn, stmt_relative_id_regex is without the prefix: "arn:aws:sts::"
            if regex.search(service_resource.get_resource_arn()) is not None and isinstance(
                service_resource, FederatedUserPrincipal
            ):
                yield service_resource

    @classmethod
    def load_from_single_stmt(
        cls,
        _logger: Logger,
        stmt_ctx: StmtResourcesToResolveCtx,
    ) -> ServiceResourcesResolverBase:
        resolved_federated_users_actions: Dict[FederatedUserPrincipal, ResolvedFederatedUserActions] = {}
        federated_user_actions = set(
            [
                resolved_stmt_action
                for resolved_stmt_action in stmt_ctx.resolved_stmt_actions
                if isinstance(resolved_stmt_action, FederatedUserAction)
            ]
        )

        for stmt_relative_id_regex in stmt_ctx.stmt_relative_id_resource_regexes:
            yield_federated_users = (
                FederatedUserServiceResourcesResolver._yield_resolve_resources_from_stmt_relative_id_regex(
                    stmt_relative_id_regex, stmt_ctx.service_resources
                )
            )
            for yield_federated_user in yield_federated_users:
                resolved_federated_users_actions[yield_federated_user] = ResolvedFederatedUserActions.load(
                    federated_user_actions
                )

        resolved_stmt: ResolvedSingleStmt = ResolvedSingleStmt.load(stmt_ctx, resolved_federated_users_actions)  # type: ignore
        return cls(resolved_stmts=[FederatedUserResolvedStmt(resolved_stmt=resolved_stmt)])
