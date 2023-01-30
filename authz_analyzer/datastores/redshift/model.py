from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Set

from authz_analyzer.models import PermissionLevel

IdentityId = int


class IdentityType(Enum):
    UNKNOWN = "UNKNOWN"
    USER = "USER"
    GROUP = "GROUP"
    ROLE = "ROLE"


class Privilege(Enum):
    # values - https://docs.aws.amazon.com/redshift/latest/dg/r_SVV_RELATION_PRIVILEGES.html
    SELECT = auto()
    INSERT = auto()
    UPDATE = auto()
    DELETE = auto()
    REFERENCES = auto()
    DROP = auto()
    # https: // docs.aws.amazon.com / redshift / latest / dg / r_Privileges.html
    TEMPORARY = auto()
    CREATE = auto()
    USAGE = auto()
    # additional values - https://docs.aws.amazon.com/redshift/latest/dg/r_SVV_DEFAULT_PRIVILEGES.html
    RULE = auto()
    TRIGGER = auto()
    EXECUTE = auto()


PERMISSION_LEVEL_MAP = {
    Privilege.SELECT.name: PermissionLevel.READ,
    Privilege.INSERT.name: PermissionLevel.WRITE,
    Privilege.UPDATE.name: PermissionLevel.WRITE,
    Privilege.DELETE.name: PermissionLevel.WRITE,
    Privilege.REFERENCES.name: PermissionLevel.READ,
    Privilege.DROP.name: PermissionLevel.WRITE,
    Privilege.TEMPORARY.name: PermissionLevel.WRITE,
    Privilege.CREATE.name: PermissionLevel.WRITE,
    Privilege.USAGE.name: PermissionLevel.WRITE,
    Privilege.RULE.name: PermissionLevel.WRITE,
    Privilege.TRIGGER.name: PermissionLevel.READ,
    Privilege.EXECUTE.name: PermissionLevel.FULL,
}


@dataclass
class ResourcePermission:
    """Define a resource, e.g. a table, the permission level and the DB permissions.
    The list is db.schema.table.
    """

    name: List[str]
    permission_level: PermissionLevel
    db_permissions: List[str]

    def __hash__(self) -> int:
        return hash(str(self.name))


@dataclass
class DBIdentity:
    """Define an identity, e.g. User, Group, role."""

    id_: IdentityId
    name: str
    type: IdentityType
    relations: Set[DBIdentity]

    @classmethod
    def new(cls, id_: IdentityId, name: str, identity_type: IdentityType, relations: Set[DBIdentity]):
        """Create a new DBIdentity."""
        return cls(id_=id_, name=name, type=identity_type, relations=relations)

    def add_relation(self, relations: DBIdentity):
        self.relations.add(relations)

    def __hash__(self) -> int:
        return hash(self.id_)


@dataclass
class AuthorizationModel:
    """Define the authorization model.
    Map a role to the roles it has, and the grants it has.
    Map a role to the grants it has.
    """

    identity_to_identities: Dict[DBIdentity, Set[DBIdentity]]
    identity_to_resource_privilege: Dict[IdentityId, Dict[str, Set[ResourcePermission]]]
