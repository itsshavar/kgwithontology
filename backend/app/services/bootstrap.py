from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.security import Permission, Role, RolePermission

DEFAULT_ROLES = {
    "Admin": ["*"],
    "Ontology Engineer": ["ontology:read", "ontology:write", "documents:read", "kg:read"],
    "Data Analyst": ["documents:read", "documents:write", "kg:read", "kg:write", "query:execute"],
    "Viewer": ["documents:read", "ontology:read", "kg:read"],
    "API User": ["api:access", "query:execute"],
}


def bootstrap_rbac(db: Session) -> None:
    permissions: dict[str, Permission] = {}
    for codes in DEFAULT_ROLES.values():
        for code in codes:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if not permission:
                permission = Permission(code=code, description=f"Allows {code}")
                db.add(permission)
                db.flush()
            permissions[code] = permission
    for role_name, codes in DEFAULT_ROLES.items():
        role = db.scalar(select(Role).where(Role.name == role_name))
        if not role:
            role = Role(name=role_name, description=f"Built-in {role_name} role")
            db.add(role)
            db.flush()
        for code in codes:
            exists = db.scalar(select(RolePermission).where(RolePermission.role_id == role.id, RolePermission.permission_id == permissions[code].id))
            if not exists:
                db.add(RolePermission(role_id=role.id, permission_id=permissions[code].id))
    db.commit()
