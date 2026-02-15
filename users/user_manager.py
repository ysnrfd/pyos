"""
User Manager Module

Implements multi-user support with:
- User and group management
- Password hashing
- Session management
- Role-based access control

Author: YSNRFD
Version: 1.0.0
"""

import hashlib
import threading
import time
import secrets
from dataclasses import dataclass, field
from typing import Optional, Any, List
from enum import Enum

from pyos.core.registry import Subsystem, SubsystemState
from pyos.core.config_loader import get_config
from pyos.exceptions import (
    AuthenticationError,
    AuthorizationError,
)
from pyos.logger import Logger, get_logger


class Role(Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


@dataclass
class Group:
    """A user group."""
    gid: int
    name: str
    members: List[int] = field(default_factory=list)


@dataclass
class User:
    """A system user."""
    uid: int
    username: str
    password_hash: str
    gid: int
    home: str
    shell: str = "/bin/pysh"
    roles: set[Role] = field(default_factory=lambda: {Role.USER})
    locked: bool = False
    last_login: Optional[float] = None
    failed_attempts: int = 0


@dataclass
class Session:
    """A user session."""
    session_id: str
    uid: int
    username: str
    created_at: float
    expires_at: float
    pid: int = 0  # Associated process
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class UserManager(Subsystem):
    """
    User Management Subsystem.
    
    Provides:
    - User and group management
    - Authentication
    - Session management
    - Role-based access control
    
    Example:
        >>> um = UserManager()
        >>> um.initialize()
        >>> session = um.login('root', 'password')
    """
    
    def __init__(self):
        super().__init__('users')
        self._users: dict[int, User] = {}
        self._users_by_name: dict[str, int] = {}
        self._groups: dict[int, Group] = {}
        self._groups_by_name: dict[str, int] = {}
        self._sessions: dict[str, Session] = {}
        self._sessions_by_uid: dict[int, list[str]] = {}
        
        self._next_uid = 1
        self._next_gid = 1
        self._lock = threading.Lock()
        
        self._session_timeout = 3600  # 1 hour
        self._max_failed_attempts = 5
    
    def initialize(self) -> None:
        """Initialize the user manager."""
        self._logger.info("Initializing user manager")
        
        # Create root user
        self._create_root_user()
        
        # Create standard groups
        self._create_standard_groups()
        
        self.set_state(SubsystemState.INITIALIZED)
        self._logger.info("User manager initialized")
    
    def _create_root_user(self) -> None:
        """Create the root user."""
        root = User(
            uid=0,
            username="root",
            password_hash=self._hash_password("root"),
            gid=0,
            home="/root",
            shell="/bin/pysh",
            roles={Role.ADMIN, Role.USER}
        )
        
        self._users[0] = root
        self._users_by_name["root"] = 0
        
        # Create root group
        root_group = Group(gid=0, name="root", members=[0])
        self._groups[0] = root_group
        self._groups_by_name["root"] = 0
    
    def _create_standard_groups(self) -> None:
        """Create standard UNIX groups."""
        groups = [
            ("wheel", 1),
            ("users", 100),
            ("nobody", 65534),
        ]
        
        for name, gid in groups:
            if gid not in self._groups:
                group = Group(gid=gid, name=name)
                self._groups[gid] = group
                self._groups_by_name[name] = gid
    
    def start(self) -> None:
        """Start the user manager."""
        self.set_state(SubsystemState.RUNNING)
        self._logger.info("User manager started")
    
    def stop(self) -> None:
        """Stop the user manager."""
        self._logger.info("Stopping user manager")
        self._sessions.clear()
        self.set_state(SubsystemState.STOPPED)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._sessions.clear()
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(
        self,
        username: str,
        password: str,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        home: Optional[str] = None,
        roles: Optional[set[Role]] = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            username: Username
            password: Plain text password
            uid: User ID (auto-assigned if None)
            gid: Primary group ID
            home: Home directory
            roles: User roles
        
        Returns:
            Created User
        
        Raises:
            ValueError: If username already exists
        """
        with self._lock:
            if username in self._users_by_name:
                raise ValueError(f"User '{username}' already exists")
            
            # Assign UID
            if uid is None:
                uid = self._next_uid
                while uid in self._users:
                    uid += 1
                self._next_uid = uid + 1
            
            # Assign GID
            if gid is None:
                gid = 100  # users group
            
            # Set home directory
            if home is None:
                config = get_config()
                home = f"{config.users.home_prefix}/{username}"
            
            # Create user
            user = User(
                uid=uid,
                username=username,
                password_hash=self._hash_password(password),
                gid=gid,
                home=home,
                roles=roles or {Role.USER}
            )
            
            self._users[uid] = user
            self._users_by_name[username] = uid
            
            # Add to group
            if gid in self._groups:
                self._groups[gid].members.append(uid)
            
            self._logger.info(
                f"Created user '{username}'",
                context={'uid': uid, 'gid': gid}
            )
            
            return user
    
    def delete_user(self, username: str) -> None:
        """Delete a user."""
        with self._lock:
            uid = self._users_by_name.get(username)
            if uid is None:
                raise ValueError(f"User '{username}' not found")
            
            if uid == 0:
                raise ValueError("Cannot delete root user")
            
            # Remove from groups
            for group in self._groups.values():
                if uid in group.members:
                    group.members.remove(uid)
            
            # End sessions
            for session_id in self._sessions_by_uid.get(uid, []):
                self._sessions.pop(session_id, None)
            self._sessions_by_uid.pop(uid, None)
            
            del self._users[uid]
            del self._users_by_name[username]
            
            self._logger.info(f"Deleted user '{username}'")
    
    def get_user(self, uid: int) -> Optional[User]:
        """Get a user by UID."""
        return self._users.get(uid)
    
    def get_user_by_name(self, username: str) -> Optional[User]:
        """Get a user by username."""
        uid = self._users_by_name.get(username)
        if uid is not None:
            return self._users.get(uid)
        return None
    
    def create_group(self, name: str, gid: Optional[int] = None) -> Group:
        """Create a new group."""
        with self._lock:
            if name in self._groups_by_name:
                raise ValueError(f"Group '{name}' already exists")
            
            if gid is None:
                gid = self._next_gid
                while gid in self._groups:
                    gid += 1
                self._next_gid = gid + 1
            
            group = Group(gid=gid, name=name)
            
            self._groups[gid] = group
            self._groups_by_name[name] = gid
            
            self._logger.info(f"Created group '{name}'", context={'gid': gid})
            
            return group
    
    def get_group(self, gid: int) -> Optional[Group]:
        """Get a group by GID."""
        return self._groups.get(gid)
    
    def add_user_to_group(self, uid: int, gid: int) -> None:
        """Add a user to a group."""
        with self._lock:
            group = self._groups.get(gid)
            if group is None:
                raise ValueError(f"Group {gid} not found")
            
            if uid not in group.members:
                group.members.append(uid)
    
    def login(self, username: str, password: str) -> Session:
        """
        Authenticate a user and create a session.
        
        Args:
            username: Username
            password: Plain text password
        
        Returns:
            Session object
        
        Raises:
            AuthenticationError: If authentication fails
        """
        user = self.get_user_by_name(username)
        
        if user is None:
            raise AuthenticationError("User not found", username=username)
        
        if user.locked:
            raise AuthenticationError("Account locked", username=username)
        
        # Check failed attempts
        if user.failed_attempts >= self._max_failed_attempts:
            user.locked = True
            raise AuthenticationError(
                "Account locked due to failed attempts",
                username=username
            )
        
        # Verify password
        if self._hash_password(password) != user.password_hash:
            user.failed_attempts += 1
            raise AuthenticationError("Invalid password", username=username)
        
        # Reset failed attempts
        user.failed_attempts = 0
        user.last_login = time.time()
        
        # Create session
        session_id = secrets.token_hex(16)
        now = time.time()
        
        session = Session(
            session_id=session_id,
            uid=user.uid,
            username=user.username,
            created_at=now,
            expires_at=now + self._session_timeout
        )
        
        with self._lock:
            self._sessions[session_id] = session
            if user.uid not in self._sessions_by_uid:
                self._sessions_by_uid[user.uid] = []
            self._sessions_by_uid[user.uid].append(session_id)
        
        self._logger.info(
            f"User '{username}' logged in",
            context={'session_id': session_id[:8]}
        )
        
        return session
    
    def logout(self, session_id: str) -> bool:
        """End a session."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                uid_sessions = self._sessions_by_uid.get(session.uid, [])
                if session_id in uid_sessions:
                    uid_sessions.remove(session_id)
                
                self._logger.info(
                    f"User '{session.username}' logged out",
                    context={'session_id': session_id[:8]}
                )
                return True
            return False
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if session and session.is_expired():
            self.logout(session_id)
            return None
        return session
    
    def validate_session(self, session_id: str) -> bool:
        """Validate a session."""
        session = self.get_session(session_id)
        return session is not None and not session.is_expired()
    
    def refresh_session(self, session_id: str) -> bool:
        """Refresh a session's expiration."""
        session = self._sessions.get(session_id)
        if session:
            session.expires_at = time.time() + self._session_timeout
            return True
        return False
    
    def change_password(
        self,
        username: str,
        old_password: str,
        new_password: str
    ) -> None:
        """Change a user's password."""
        user = self.get_user_by_name(username)
        
        if user is None:
            raise ValueError(f"User '{username}' not found")
        
        # Verify old password
        if self._hash_password(old_password) != user.password_hash:
            raise AuthenticationError("Invalid password", username=username)
        
        user.password_hash = self._hash_password(new_password)
        
        self._logger.info(f"Changed password for '{username}'")
    
    def check_permission(
        self,
        uid: int,
        resource: str,
        action: str
    ) -> bool:
        """
        Check if a user has permission for an action.
        
        Args:
            uid: User ID
            resource: Resource identifier
            action: Action to perform
        
        Returns:
            True if permitted
        """
        user = self.get_user(uid)
        
        if user is None:
            return False
        
        # Root has all permissions
        if user.uid == 0:
            return True
        
        # Admin has most permissions
        if Role.ADMIN in user.roles:
            return True
        
        # Check role-based permissions
        permissions = {
            (Role.USER, "file", "read"),
            (Role.USER, "file", "write"),
            (Role.USER, "process", "create"),
            (Role.USER, "process", "kill"),
        }
        
        return (min(user.roles, key=lambda r: list(Role).index(r)), resource, action) in permissions
    
    def get_user_sessions(self, uid: int) -> List[Session]:
        """Get all sessions for a user."""
        session_ids = self._sessions_by_uid.get(uid, [])
        return [
            self._sessions[sid]
            for sid in session_ids
            if sid in self._sessions
        ]
    
    def list_users(self) -> List[dict[str, Any]]:
        """List all users."""
        return [
            {
                'uid': user.uid,
                'username': user.username,
                'gid': user.gid,
                'home': user.home,
                'shell': user.shell,
                'roles': [r.value for r in user.roles],
                'locked': user.locked,
            }
            for user in self._users.values()
        ]
    
    def list_groups(self) -> List[dict[str, Any]]:
        """List all groups."""
        return [
            {
                'gid': group.gid,
                'name': group.name,
                'members': len(group.members),
            }
            for group in self._groups.values()
        ]
    
    def get_stats(self) -> dict[str, Any]:
        """Get user manager statistics."""
        return {
            'total_users': len(self._users),
            'total_groups': len(self._groups),
            'active_sessions': len(self._sessions),
        }
