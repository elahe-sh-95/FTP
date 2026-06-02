"""
Wing FTP Server - Tree-Based Access Control System
===================================================

This module implements a hierarchical access control model for organizing
users, roles, and permissions in a Wing FTP Server environment.

Author: Senior Systems Architect
Date: 2024
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import json


class Role(Enum):
    """Enumeration of user roles in the organization."""
    GROUP_MANAGER = "group_manager"
    PRODUCT_MANAGER = "product_manager"
    TECH_LEAD = "tech_lead"
    TEAM_MEMBER = "team_member"


class ConnectionMethod(Enum):
    """Allowed connection methods for users."""
    VDI = "vdi"
    LOCAL_VPN = "local_vpn"
    LOCAL_ONLY = "local_only"


@dataclass
class FTPPermissions:
    """FTP directory permissions for a user role."""
    personal_directory: str
    shared_directories: List[str]
    employee_personal_access: bool = False  # Can access team members' personal dirs
    
    def get_all_directories(self) -> List[str]:
        """Return all accessible directories."""
        dirs = [self.personal_directory] if self.personal_directory else []
        dirs.extend(self.shared_directories)
        return dirs


@dataclass
class AccessProfile:
    """Complete access profile including FTP permissions and connection methods."""
    role: Role
    ftp_permissions: FTPPermissions
    allowed_connection_methods: List[ConnectionMethod]
    
    def can_use_vdi(self) -> bool:
        """Check if VDI access is allowed."""
        return ConnectionMethod.VDI in self.allowed_connection_methods
    
    def can_use_local_vpn(self) -> bool:
        """Check if local VPN access is allowed."""
        return ConnectionMethod.LOCAL_VPN in self.allowed_connection_methods


@dataclass
class TreeNode:
    """Represents a node in the organizational hierarchy tree."""
    user_id: str
    name: str
    role: Role
    access_profile: AccessProfile
    parent: Optional['TreeNode'] = None
    children: List['TreeNode'] = field(default_factory=list)
    direct_reports: List[str] = field(default_factory=list)  # User IDs of direct reports
    
    def add_child(self, child: 'TreeNode') -> None:
        """Add a child node to this node."""
        child.parent = self
        self.children.append(child)
        if child.user_id not in self.direct_reports:
            self.direct_reports.append(child.user_id)
    
    def get_depth(self) -> int:
        """Get the depth of this node in the tree (root = 0)."""
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth
    
    def to_dict(self) -> Dict:
        """Convert node to dictionary representation."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "role": self.role.value,
            "access_profile": {
                "role": self.access_profile.role.value,
                "ftp_permissions": {
                    "personal_directory": self.access_profile.ftp_permissions.personal_directory,
                    "shared_directories": self.access_profile.ftp_permissions.shared_directories,
                    "employee_personal_access": self.access_profile.ftp_permissions.employee_personal_access
                },
                "allowed_connection_methods": [m.value for m in self.access_profile.allowed_connection_methods]
            },
            "direct_reports": self.direct_reports,
            "children_count": len(self.children)
        }


class OrganizationTree:
    """
    Hierarchical tree structure representing the organization.
    Provides methods for traversal and permission resolution.
    """
    
    def __init__(self):
        self.root: Optional[TreeNode] = None
        self.user_index: Dict[str, TreeNode] = {}  # Fast lookup by user_id
        self.role_index: Dict[Role, List[TreeNode]] = {}  # Fast lookup by role
        
    def build_tree(self) -> None:
        """Build the complete organizational tree."""
        
        # Define access profiles for each role
        pm_profile = AccessProfile(
            role=Role.PRODUCT_MANAGER,
            ftp_permissions=FTPPermissions(
                personal_directory="PM_personal",
                shared_directories=["PM_share", "techlead_share", "shared_access"],
                employee_personal_access=False
            ),
            allowed_connection_methods=[ConnectionMethod.VDI, ConnectionMethod.LOCAL_VPN]
        )
        
        tl_profile = AccessProfile(
            role=Role.TECH_LEAD,
            ftp_permissions=FTPPermissions(
                personal_directory="TL_personal",
                shared_directories=["TL_share", "shared_access"],
                employee_personal_access=True
            ),
            allowed_connection_methods=[ConnectionMethod.VDI, ConnectionMethod.LOCAL_VPN]
        )
        
        team_member_profile = AccessProfile(
            role=Role.TEAM_MEMBER,
            ftp_permissions=FTPPermissions(
                personal_directory="Employee_personal",
                shared_directories=["shared_access"],
                employee_personal_access=False
            ),
            allowed_connection_methods=[ConnectionMethod.LOCAL_ONLY]
        )
        
        gm_profile = AccessProfile(
            role=Role.GROUP_MANAGER,
            ftp_permissions=FTPPermissions(
                personal_directory="GM_personal",
                shared_directories=["PM_share", "TL_share", "techlead_share", "shared_access"],
                employee_personal_access=True
            ),
            allowed_connection_methods=[ConnectionMethod.VDI, ConnectionMethod.LOCAL_VPN]
        )
        
        # Create root node - Group Manager
        self.root = TreeNode(
            user_id="naderpour",
            name="Dr. Naderpour",
            role=Role.GROUP_MANAGER,
            access_profile=gm_profile
        )
        self._index_node(self.root)
        
        # Create Product Managers
        pms = [
            TreeNode("mokhtari", "Ms. Mokhtari", Role.PRODUCT_MANAGER, pm_profile),
            TreeNode("mokhtari_m", "Ms. Mirhosseini", Role.PRODUCT_MANAGER, pm_profile),
            TreeNode("dehghani_p", "Mr. Dehghani", Role.PRODUCT_MANAGER, pm_profile),
            TreeNode("arabi", "Mr. Arabi", Role.PRODUCT_MANAGER, pm_profile),
        ]
        
        for pm in pms:
            self.root.add_child(pm)
            self._index_node(pm)
        
        # Create Tech Leads
        tls = [
            TreeNode("azimi", "Mr. Azimi", Role.TECH_LEAD, tl_profile),
            TreeNode("jafari", "Mr. Jafari", Role.TECH_LEAD, tl_profile),
            TreeNode("bilalzadeh", "Mr. Bilalzadeh", Role.TECH_LEAD, tl_profile),
            TreeNode("nateghi", "Mr. Nateghi", Role.TECH_LEAD, tl_profile),
            TreeNode("asadi", "Mr. Asadi", Role.TECH_LEAD, tl_profile),
            TreeNode("kalami", "Mr. Kalami", Role.TECH_LEAD, tl_profile),
            TreeNode("shams", "Ms. Shams", Role.TECH_LEAD, tl_profile),
            TreeNode("movahedi", "Mr. Movahedi", Role.TECH_LEAD, tl_profile),
            TreeNode("ghaedi", "Mr. Ghaedi", Role.TECH_LEAD, tl_profile),
            TreeNode("dehghani2_tl", "Mr. Dehghani2", Role.TECH_LEAD, tl_profile),
        ]
        
        # Add TLs as children of PMs (distribute evenly)
        for i, tl in enumerate(tls):
            pm_parent = pms[i % len(pms)]
            pm_parent.add_child(tl)
            self._index_node(tl)
        
        # Create Team Members and assign to TLs
        # Under Mr. Jafari
        jafari_team = [
            TreeNode("dehghani2_tm", "Mr. Dehghani2", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("shahsavan", "Ms. Shahsavan", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("darvishzadeh", "Mr. Darvishzadeh", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("dashti", "Ms. Dashti", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("abolhasanzadeh", "Mr. Abolhasanzadeh", Role.TEAM_MEMBER, team_member_profile),
        ]
        jafari_node = self.user_index["jafari"]
        for member in jafari_team:
            jafari_node.add_child(member)
            self._index_node(member)
        
        # Under Ms. Shams
        shams_team = [
            TreeNode("deldar", "Mr. Deldar", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("karimi", "Mr. Karimi", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("babaei", "Mr. Babaei", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("ghazanfari", "Mr. Ghazanfari", Role.TEAM_MEMBER, team_member_profile),
        ]
        shams_node = self.user_index["shams"]
        for member in shams_team:
            shams_node.add_child(member)
            self._index_node(member)
        
        # Under Mr. Azimi
        azimi_team = [
            TreeNode("aghashahi_az", "Ms. Aghashahi", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("rouhi", "Mr. Rouhi", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("rahimifard", "Mr. Rahimifard", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("khabiri", "Mr. Khabiri", Role.TEAM_MEMBER, team_member_profile),
        ]
        azimi_node = self.user_index["azimi"]
        for member in azimi_team:
            azimi_node.add_child(member)
            self._index_node(member)
        
        # Under Mr. Bilalzadeh & Mr. Nateghi (Shared)
        bilal_nateghi_team = [
            TreeNode("zare", "Mr. Zare", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("aghashahi_bn", "Ms. Aghashahi", Role.TEAM_MEMBER, team_member_profile),
        ]
        bilal_node = self.user_index["bilalzadeh"]
        nateghi_node = self.user_index["nateghi"]
        for member in bilal_nateghi_team:
            bilal_node.add_child(member)
            nateghi_node.add_child(member)  # Shared reporting
            self._index_node(member)
        
        # Under Mr. Asadi & Mr. Kalami (Shared)
        asadi_kalami_team = [
            TreeNode("mahdieh", "Ms. Mahdieh", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("hashemi", "Mr. Hashemi", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("naghizadeh", "Mr. Naghizadeh", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("modarres", "Mr. Modarres", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("ghamsheh", "Mr. Ghamsheh", Role.TEAM_MEMBER, team_member_profile),
        ]
        asadi_node = self.user_index["asadi"]
        kalami_node = self.user_index["kalami"]
        for member in asadi_kalami_team:
            asadi_node.add_child(member)
            kalami_node.add_child(member)  # Shared reporting
            self._index_node(member)
        
        # Under Mr. Movahedi
        movahedi_team = [
            TreeNode("mohammadi", "Mr. Mohammadi", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("mojibzadeh", "Mr. Mojibzadeh", Role.TEAM_MEMBER, team_member_profile),
            TreeNode("faraji", "Mr. Faraji", Role.TEAM_MEMBER, team_member_profile),
        ]
        movahedi_node = self.user_index["movahedi"]
        for member in movahedi_team:
            movahedi_node.add_child(member)
            self._index_node(member)
    
    def _index_node(self, node: TreeNode) -> None:
        """Add node to indexes for fast lookup."""
        self.user_index[node.user_id] = node
        
        if node.role not in self.role_index:
            self.role_index[node.role] = []
        self.role_index[node.role].append(node)
    
    def get_user_node(self, user_id: str) -> Optional[TreeNode]:
        """Get a user node by user ID."""
        return self.user_index.get(user_id)
    
    def resolve_permissions(self, user_id: str) -> Optional[Dict]:
        """
        Resolve FTP permissions and connection methods for a user.
        
        Args:
            user_id: The unique identifier of the user
            
        Returns:
            Dictionary containing permissions and connection methods, or None if user not found
        """
        node = self.get_user_node(user_id)
        if not node:
            return None
        
        result = {
            "user_id": user_id,
            "name": node.name,
            "role": node.role.value,
            "accessible_directories": node.access_profile.ftp_permissions.get_all_directories(),
            "can_access_employee_personal": node.access_profile.ftp_permissions.employee_personal_access,
            "allowed_connection_methods": [m.value for m in node.access_profile.allowed_connection_methods],
            "vdi_allowed": node.access_profile.can_use_vdi(),
            "local_vpn_allowed": node.access_profile.can_use_local_vpn()
        }
        
        # If Tech Lead, add list of direct reports whose personal directories they can access
        if node.role == Role.TECH_LEAD and node.access_profile.ftp_permissions.employee_personal_access:
            result["accessible_employee_dirs"] = [
                self.user_index[report_id].name 
                for report_id in node.direct_reports
                if report_id in self.user_index
            ]
        
        return result
    
    def traverse_bfs(self, start_node: Optional[TreeNode] = None) -> List[TreeNode]:
        """
        Breadth-First Search traversal of the tree.
        
        Args:
            start_node: Node to start traversal from (default: root)
            
        Returns:
            List of nodes in BFS order
        """
        if start_node is None:
            start_node = self.root
        
        if not start_node:
            return []
        
        result = []
        queue = [start_node]
        visited = set()
        
        while queue:
            node = queue.pop(0)
            if node.user_id in visited:
                continue
            visited.add(node.user_id)
            result.append(node)
            
            for child in node.children:
                if child.user_id not in visited:
                    queue.append(child)
        
        return result
    
    def traverse_dfs(self, start_node: Optional[TreeNode] = None) -> List[TreeNode]:
        """
        Depth-First Search traversal of the tree.
        
        Args:
            start_node: Node to start traversal from (default: root)
            
        Returns:
            List of nodes in DFS order
        """
        if start_node is None:
            start_node = self.root
        
        if not start_node:
            return []
        
        result = []
        stack = [start_node]
        visited = set()
        
        while stack:
            node = stack.pop()
            if node.user_id in visited:
                continue
            visited.add(node.user_id)
            result.append(node)
            
            # Add children in reverse order to maintain left-to-right traversal
            for child in reversed(node.children):
                if child.user_id not in visited:
                    stack.append(child)
        
        return result
    
    def find_subtree(self, user_id: str) -> Optional[TreeNode]:
        """
        Find and return the subtree rooted at the given user.
        
        Args:
            user_id: The user ID to find the subtree for
            
        Returns:
            The node representing the root of the subtree, or None if not found
        """
        return self.get_user_node(user_id)
    
    def get_all_users_by_role(self, role: Role) -> List[TreeNode]:
        """Get all users with a specific role."""
        return self.role_index.get(role, [])
    
    def to_json(self, indent: int = 2) -> str:
        """Convert the entire tree to JSON representation."""
        if not self.root:
            return json.dumps({"error": "Tree not built"}, indent=indent)
        
        def node_to_dict(node: TreeNode) -> Dict:
            result = node.to_dict()
            if node.children:
                result["children"] = [node_to_dict(child) for child in node.children]
            return result
        
        tree_dict = {
            "organization": "Wing FTP Server Access Control",
            "root": node_to_dict(self.root),
            "total_users": len(self.user_index),
            "roles_summary": {
                role.value: len(nodes) for role, nodes in self.role_index.items()
            }
        }
        
        return json.dumps(tree_dict, indent=indent)
    
    def export_for_wing_ftp(self) -> Dict:
        """
        Export configuration in a format suitable for Wing FTP Server integration.
        This can be used with Wing FTP's Lua scripting or REST API.
        """
        config = {
            "users": [],
            "groups": [],
            "directories": []
        }
        
        # Generate user configurations
        for user_id, node in self.user_index.items():
            user_config = {
                "username": user_id,
                "name": node.name,
                "role": node.role.value,
                "home_directory": f"/{node.access_profile.ftp_permissions.personal_directory}/{user_id}" if node.access_profile.ftp_permissions.personal_directory else "/",
                "accessible_paths": [
                    f"/{dir_path}" for dir_path in node.access_profile.ftp_permissions.get_all_directories()
                ],
                "connection_restrictions": {
                    "allow_vdi": node.access_profile.can_use_vdi(),
                    "allow_local_vpn": node.access_profile.can_use_local_vpn(),
                    "ip_restrictions": []  # Can be populated with specific IP ranges
                }
            }
            config["users"].append(user_config)
        
        # Generate group configurations
        for role, nodes in self.role_index.items():
            group_config = {
                "group_name": f"{role.value}s",
                "members": [node.user_id for node in nodes],
                "permissions": {
                    "read": True,
                    "write": True,
                    "delete": role in [Role.GROUP_MANAGER, Role.PRODUCT_MANAGER],
                    "admin": role == Role.GROUP_MANAGER
                }
            }
            config["groups"].append(group_config)
        
        # Generate directory configurations
        all_dirs = set()
        for node in self.user_index.values():
            all_dirs.update(node.access_profile.ftp_permissions.get_all_directories())
        
        for dir_path in all_dirs:
            dir_config = {
                "path": f"/{dir_path}",
                "access_rules": []
            }
            config["directories"].append(dir_config)
        
        return config


# Example usage and demonstration
if __name__ == "__main__":
    # Initialize and build the organization tree
    org_tree = OrganizationTree()
    org_tree.build_tree()
    
    print("=" * 80)
    print("WING FTP SERVER - TREE-BASED ACCESS CONTROL SYSTEM")
    print("=" * 80)
    
    # Demonstrate permission resolution for different users
    test_users = ["naderpour", "mokhtari", "jafari", "shahsavan", "zare"]
    
    print("\n1. PERMISSION RESOLUTION EXAMPLES:")
    print("-" * 80)
    
    for user_id in test_users:
        perms = org_tree.resolve_permissions(user_id)
        if perms:
            print(f"\nUser: {perms['name']} ({perms['user_id']})")
            print(f"  Role: {perms['role']}")
            print(f"  Accessible Directories: {', '.join(perms['accessible_directories'])}")
            print(f"  Can Access Employee Personal Dirs: {perms['can_access_employee_personal']}")
            if 'accessible_employee_dirs' in perms:
                print(f"  Accessible Employee Dirs: {', '.join(perms['accessible_employee_dirs'])}")
            print(f"  Allowed Connection Methods: {', '.join(perms['allowed_connection_methods'])}")
            print(f"  VDI Allowed: {perms['vdi_allowed']}")
            print(f"  Local VPN Allowed: {perms['local_vpn_allowed']}")
    
    # Demonstrate tree traversal
    print("\n\n2. TREE TRAVERSAL (BFS - First 10 users):")
    print("-" * 80)
    bfs_nodes = org_tree.traverse_bfs()[:10]
    for i, node in enumerate(bfs_nodes, 1):
        print(f"{i}. {node.name} ({node.role.value})")
    
    # Demonstrate subtree extraction
    print("\n\n3. SUBTREE EXAMPLE (Mr. Jafari's team):")
    print("-" * 80)
    jafari_subtree = org_tree.find_subtree("jafari")
    if jafari_subtree:
        print(f"Tech Lead: {jafari_subtree.name}")
        print(f"Direct Reports: {', '.join(jafari_subtree.direct_reports)}")
        for report_id in jafari_subtree.direct_reports:
            report_node = org_tree.get_user_node(report_id)
            if report_node:
                print(f"  - {report_node.name}")
    
    # Export for Wing FTP
    print("\n\n4. WING FTP CONFIGURATION EXPORT:")
    print("-" * 80)
    wing_ftp_config = org_tree.export_for_wing_ftp()
    print(f"Total Users: {len(wing_ftp_config['users'])}")
    print(f"Total Groups: {len(wing_ftp_config['groups'])}")
    print(f"Total Directories: {len(wing_ftp_config['directories'])}")
    
    # Save full JSON representation
    print("\n\n5. SAVING FULL TREE STRUCTURE TO JSON...")
    print("-" * 80)
    json_output = org_tree.to_json()
    with open("organization_tree.json", "w") as f:
        f.write(json_output)
    print("Saved to: organization_tree.json")
    
    # Save Wing FTP configuration
    with open("wing_ftp_config.json", "w") as f:
        json.dump(wing_ftp_config, f, indent=2)
    print("Saved to: wing_ftp_config.json")
    
    print("\n" + "=" * 80)
    print("IMPLEMENTATION COMPLETE")
    print("=" * 80)
