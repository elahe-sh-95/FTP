# Wing FTP Server - Tree-Based Access Control Implementation Guide

## Executive Summary

This document provides a comprehensive guide for implementing a hierarchical access control system in Wing FTP Server based on the organizational structure provided. The solution includes a Python-based tree data structure, permission resolution algorithms, and specific recommendations for Wing FTP integration.

---

## 1. Organizational Hierarchy Overview

```
Dr. Naderpour (Group Manager)
├── Product Managers (4)
│   ├── Ms. Mokhtari
│   ├── Ms. Mirhosseini
│   ├── Mr. Dehghani
│   └── Mr. Arabi
└── Tech Leads (10) → Team Members (23)
    ├── Mr. Azimi (4 reports)
    ├── Mr. Jafari (5 reports)
    ├── Mr. Bilalzadeh & Mr. Nateghi (2 shared reports)
    ├── Mr. Asadi & Mr. Kalami (5 shared reports)
    ├── Ms. Shams (4 reports)
    ├── Mr. Movahedi (3 reports)
    ├── Mr. Ghaedi
    └── Mr. Dehghani2 (TL role)
```

**Total Users:** 38 (1 GM + 4 PMs + 10 TLs + 23 Team Members)

---

## 2. Data Structure Design

### 2.1 Core Classes

#### TreeNode
Represents each user in the organizational hierarchy.

```python
@dataclass
class TreeNode:
    user_id: str                    # Unique identifier
    name: str                       # Full name
    role: Role                      # Enum: GROUP_MANAGER, PRODUCT_MANAGER, TECH_LEAD, TEAM_MEMBER
    access_profile: AccessProfile   # Permissions and connection methods
    parent: Optional[TreeNode]      # Reference to manager
    children: List[TreeNode]        # Direct reports
    direct_reports: List[str]       # User IDs of direct reports
```

#### AccessProfile
Defines complete access configuration for a user.

```python
@dataclass
class AccessProfile:
    role: Role
    ftp_permissions: FTPPermissions
    allowed_connection_methods: List[ConnectionMethod]
```

#### FTPPermissions
Specifies directory access rights.

```python
@dataclass
class FTPPermissions:
    personal_directory: str           # e.g., "PM_personal", "TL_personal", "Employee_personal"
    shared_directories: List[str]     # e.g., ["PM_share", "techlead_share", "shared_access"]
    employee_personal_access: bool    # Can TL/GM access team members' personal dirs?
```

### 2.2 JSON Representation

The system exports to two JSON formats:

1. **organization_tree.json** - Complete hierarchical structure
2. **wing_ftp_config.json** - Flat configuration for Wing FTP import

---

## 3. Permission Resolution Algorithm

### 3.1 Pseudocode

```
FUNCTION resolve_permissions(user_id):
    // Step 1: Lookup user node (O(1) with hash index)
    node = user_index[user_id]
    
    IF node is NULL:
        RETURN error("User not found")
    
    // Step 2: Extract access profile
    profile = node.access_profile
    
    // Step 3: Build permission result
    result = {
        user_id: user_id,
        name: node.name,
        role: profile.role,
        accessible_directories: profile.ftp_permissions.get_all_directories(),
        can_access_employee_personal: profile.ftp_permissions.employee_personal_access,
        allowed_connection_methods: profile.allowed_connection_methods,
        vdi_allowed: profile.can_use_vdi(),
        local_vpn_allowed: profile.can_use_local_vpn()
    }
    
    // Step 4: If Tech Lead, add accessible employee directories
    IF profile.role == TECH_LEAD AND profile.ftp_permissions.employee_personal_access:
        result.accessible_employee_dirs = []
        FOR EACH report_id in node.direct_reports:
            report_node = user_index[report_id]
            IF report_node exists:
                result.accessible_employee_dirs.append(report_node.name)
    
    RETURN result
```

### 3.2 Time Complexity

- **User Lookup:** O(1) - Hash table index
- **Permission Resolution:** O(n) where n = number of direct reports
- **Tree Traversal (BFS/DFS):** O(V + E) where V = users, E = reporting relationships

### 3.3 Python Implementation

See `access_control_system.py` for the complete implementation with:
- `resolve_permissions()` - Dynamic permission resolution
- `traverse_bfs()` - Breadth-first traversal
- `traverse_dfs()` - Depth-first traversal
- `find_subtree()` - Extract management subtree
- `export_for_wing_ftp()` - Configuration export

---

## 4. Access Matrix

| Role | Personal Dir | Shared Dirs | Employee Personal Access | VDI | Local VPN |
|------|-------------|-------------|-------------------------|-----|-----------|
| Group Manager | GM_personal | PM_share, TL_share, techlead_share, shared_access | ✓ (All) | ✓ | ✓ |
| Product Manager | PM_personal | PM_share, techlead_share, shared_access | ✗ | ✓ | ✓ |
| Tech Lead | TL_personal | TL_share, shared_access | ✓ (Direct reports only) | ✓ | ✓ |
| Team Member | Employee_personal | shared_access | ✗ | ✗ | ✓ (Local only) |

---

## 5. Wing FTP Server Integration Strategies

### 5.1 Option 1: Lua Scripting API (Recommended for Automation)

Wing FTP Server supports Lua scripting for automated user management.

#### Implementation Steps:

1. **Create Lua Script for User Provisioning:**

```lua
-- File: /scripts/provision_user.lua
local wftp = require("wftp")

function provision_user(username, name, role, home_dir, accessible_paths, allow_vdi, allow_local_vpn)
    -- Create user account
    local success = wftp.AddUser(username, name, "password_placeholder")
    
    if success then
        -- Set home directory
        wftp.SetUserHomeDir(username, home_dir)
        
        -- Configure directory access
        for i, path in ipairs(accessible_paths) do
            wftp.AddUserPath(username, path)
            wftp.SetPathPermission(username, path, true, true, false) -- read, write, no delete
        end
        
        -- Connection restrictions (via IP filtering)
        if not allow_vdi then
            -- Block VDI IP ranges
            wftp.AddIPFilter(username, "VDI_SUBNET", "deny")
        end
        
        if allow_local_vpn then
            -- Allow VPN 88 subnet
            wftp.AddIPFilter(username, "VPN88_SUBNET", "allow")
        end
        
        -- Add to role-based group
        local group_name = role .. "s"
        wftp.AddUserToGroup(username, group_name)
        
        return true
    end
    
    return false
end

-- Batch provisioning example
function provision_all_users_from_json(json_file)
    local users = json.decode(io.open(json_file):read("*all"))
    
    for _, user in ipairs(users.users) do
        provision_user(
            user.username,
            user.name,
            user.role,
            user.home_directory,
            user.accessible_paths,
            user.connection_restrictions.allow_vdi,
            user.connection_restrictions.allow_local_vpn
        )
    end
end
```

2. **Schedule Automatic Sync:**

```lua
-- File: /scripts/sync_organizations.lua
-- Run daily or on-demand to sync org tree with FTP users

local org_tree = json.decode(io.open("/config/organization_tree.json"):read("*all"))

function sync_users()
    -- Compare current FTP users with org tree
    -- Add new users, update permissions, disable removed users
    -- Log all changes
end

-- Trigger via Wing FTP scheduler or external API call
```

3. **Execute via Wing FTP Admin Console:**
   - Navigate to: Server → Scripts → Execute Script
   - Or schedule: Server → Scheduler → Add Task

### 5.2 Option 2: REST API Integration

Wing FTP Server v6+ provides RESTful API for remote management.

#### API Endpoints:

```bash
# Authentication
POST /api/session
{
    "username": "admin",
    "password": "admin_password"
}

# Create User
POST /api/users
{
    "name": "jafari",
    "password": "secure_password",
    "home": "/TL_personal/jafari",
    "groups": ["tech_leads"]
}

# Set Directory Access
PUT /api/users/jafari/paths
{
    "paths": [
        "/TL_personal",
        "/TL_share",
        "/shared_access"
    ]
}

# Configure IP Restrictions
PUT /api/users/jafari/ipfilter
{
    "rules": [
        {"subnet": "10.88.0.0/16", "action": "allow"},  # VPN 88
        {"subnet": "VDI_SUBNET", "action": "allow"}     # VDI network
    ]
}
```

#### Python Integration Script:

```python
import requests
import json

class WingFTPManager:
    def __init__(self, base_url, admin_user, admin_pass):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Authenticate
        resp = self.session.post(f"{base_url}/api/session", 
                                 json={"username": admin_user, "password": admin_pass})
        self.token = resp.json().get("token")
    
    def sync_organization(self, org_config_file):
        """Sync entire organization from config file"""
        with open(org_config_file) as f:
            config = json.load(f)
        
        # Create groups first
        for group in config["groups"]:
            self.create_group(group["group_name"], group["permissions"])
        
        # Then create users
        for user in config["users"]:
            self.create_or_update_user(user)
    
    def create_or_update_user(self, user_config):
        """Create new user or update existing"""
        username = user_config["username"]
        
        # Check if user exists
        resp = self.session.get(f"{self.base_url}/api/users/{username}")
        
        if resp.status_code == 404:
            # Create new user
            self.session.post(f"{self.base_url}/api/users", json={
                "name": username,
                "password": self.generate_secure_password(),
                "home": user_config["home_directory"],
                "full_name": user_config["name"]
            })
        else:
            # Update existing user
            self.session.put(f"{self.base_url}/api/users/{username}", json={
                "home": user_config["home_directory"],
                "full_name": user_config["name"]
            })
        
        # Set directory access
        self.session.put(f"{self.base_url}/api/users/{username}/paths", 
                        json={"paths": user_config["accessible_paths"]})
        
        # Configure connection restrictions
        ip_rules = []
        if user_config["connection_restrictions"]["allow_local_vpn"]:
            ip_rules.append({"subnet": "10.88.0.0/16", "action": "allow"})
        if user_config["connection_restrictions"]["allow_vdi"]:
            ip_rules.append({"subnet": "VDI_SUBNET_CIDR", "action": "allow"})
        
        self.session.put(f"{self.base_url}/api/users/{username}/ipfilter",
                        json={"rules": ip_rules})
```

### 5.3 Option 3: Active Directory Integration (Enterprise)

For organizations using Active Directory:

1. **Configure AD Groups:**
   ```
   LDAP Structure:
   OU=WingFTP_Users
   ├── CN=Group_Managers
   │   └── CN=Dr. Naderpour
   ├── CN=Product_Managers
   │   ├── CN=Ms. Mokhtari
   │   ├── CN=Ms. Mirhosseini
   │   ├── CN=Mr. Dehghani
   │   └── CN=Mr. Arabi
   ├── CN=Tech_Leads
   │   └── ... (10 TLs)
   └── CN=Team_Members
       └── ... (23 members)
   ```

2. **Wing FTP AD Configuration:**
   - Enable: Server Settings → Authentication → Active Directory
   - Map AD groups to Wing FTP groups
   - Configure group-based permissions

3. **Directory Access via AD Attributes:**
   - Use custom AD attributes for directory paths
   - Example: `ftpHomeDirectory`, `ftpAccessiblePaths`

4. **Automated Sync:**
   ```powershell
   # PowerShell script to sync AD with org tree
   Import-Module ActiveDirectory
   
   $orgTree = Get-Content "organization_tree.json" | ConvertFrom-Json
   
   foreach ($user in $orgTree.users) {
       $adUser = Get-ADUser -Identity $user.username
       
       Set-ADUser -Identity $adUser `
           -Replace @{
               "ftpHomeDirectory" = $user.home_directory
               "ftpRole" = $user.role
           }
       
       # Add to appropriate group
       Add-ADGroupMember -Identity "$($user.role)s" -Members $adUser
   }
   ```

---

## 6. Security Recommendations

### 6.1 Network Segmentation

```
VPN 88 Subnet: 10.88.0.0/16
├── VDI Pool: 10.88.10.0/24 (PMs and TLs only)
└── Local VPN: 10.88.20.0/24 (All personnel)

Access Rules:
- Team Members: ALLOW 10.88.20.0/24, DENY 10.88.10.0/24
- PMs/TLs/GM: ALLOW 10.88.0.0/16 (entire range)
```

### 6.2 Directory Permissions

```bash
# Linux/Unix-style permissions for FTP directories
/chroot/
├── GM_personal/          # 700 (rwx------) - GM only
├── PM_personal/          # 700 (rwx------) - Individual PM
├── PM_share/             # 770 (rwxrwx---) - GM + PMs
├── TL_personal/          # 700 (rwx------) - Individual TL
├── TL_share/             # 770 (rwxrwx---) - GM + TLs
├── techlead_share/       # 770 (rwxrwx---) - GM + PMs + TLs
├── shared_access/        # 775 (rwxrwxr-x) - All personnel
└── Employee_personal/    # 700 (rwx------) - Individual + their TL + GM
```

### 6.3 Audit Logging

Enable comprehensive logging in Wing FTP:

```lua
-- Custom logging script
function on_user_login(username, ip_address)
    local log_entry = {
        timestamp = os.date("!%Y-%m-%d %H:%M:%S"),
        username = username,
        ip = ip_address,
        action = "LOGIN",
        role = get_user_role(username)
    }
    
    -- Write to security log
    io.open("/var/log/wingftp/security.log", "a"):write(
        json.encode(log_entry) .. "\n"
    )
    
    -- Alert on anomalous access
    if is_vdi_ip(ip_address) and not user_can_use_vdi(username) then
        send_alert("Unauthorized VDI access attempt: " .. username)
    end
end
```

---

## 7. Deployment Workflow

### Phase 1: Setup (Week 1)
1. Install Wing FTP Server on dedicated infrastructure
2. Configure base directory structure
3. Set up SSL/TLS certificates
4. Configure backup and disaster recovery

### Phase 2: User Migration (Week 2)
1. Export current user list (if migrating from another system)
2. Run `access_control_system.py` to generate configs
3. Execute Lua script or REST API calls to provision users
4. Test authentication for sample users from each role

### Phase 3: Permission Validation (Week 3)
1. Verify directory access for each role
2. Test connection restrictions (VDI vs Local VPN)
3. Validate Tech Lead access to team member directories
4. Conduct security audit

### Phase 4: Automation & Monitoring (Week 4)
1. Deploy automated sync scripts
2. Configure alerting for unauthorized access attempts
3. Set up regular permission audits
4. Document operational procedures

---

## 8. Maintenance Procedures

### 8.1 Adding New Users

```python
# Automated user onboarding script
def onboard_new_user(employee_data):
    """
    employee_data = {
        "user_id": "new_user",
        "name": "New User",
        "role": "team_member",
        "manager_id": "jafari",  # Reports to Mr. Jafari
        "start_date": "2024-01-15"
    }
    """
    org_tree = OrganizationTree()
    org_tree.build_tree()
    
    # Find manager node
    manager = org_tree.get_user_node(employee_data["manager_id"])
    
    if not manager:
        raise Exception("Manager not found")
    
    # Create new user node with appropriate profile
    new_user = create_user_node(employee_data)
    
    # Add to tree
    manager.add_child(new_user)
    org_tree._index_node(new_user)
    
    # Provision in Wing FTP
    wing_ftp = WingFTPManager(BASE_URL, ADMIN_USER, ADMIN_PASS)
    wing_ftp.create_or_update_user(org_tree.export_for_wing_ftp()["users"][-1])
    
    # Save updated tree
    with open("organization_tree.json", "w") as f:
        f.write(org_tree.to_json())
```

### 8.2 Role Changes

When a user changes roles:
1. Update role in `organization_tree.json`
2. Re-run permission sync script
3. Revoke old permissions, grant new ones
4. Notify user of changed access

### 8.3 Offboarding

```python
def offboard_user(user_id):
    """Disable user access and transfer ownership"""
    org_tree = OrganizationTree()
    org_tree.build_tree()
    
    user_node = org_tree.get_user_node(user_id)
    if not user_node:
        return
    
    # Disable in Wing FTP (don't delete for audit trail)
    wing_ftp.disable_user(user_id)
    
    # Transfer files if team member
    if user_node.role == Role.TEAM_MEMBER and user_node.parent:
        tl_node = user_node.parent
        transfer_ownership(user_id, tl_node.user_id)
    
    # Remove from active tree (archive instead)
    archive_user_node(user_node)
```

---

## 9. Troubleshooting

### Common Issues

**Issue:** User cannot access FTP server
- **Check:** Connection method (VDI vs Local VPN)
- **Check:** IP address against allowed subnets
- **Check:** User account status in Wing FTP

**Issue:** Tech Lead cannot access team member directories
- **Check:** `employee_personal_access` flag in profile
- **Check:** Direct reports list in tree structure
- **Check:** Directory permissions on filesystem

**Issue:** Permission changes not taking effect
- **Check:** Sync script execution logs
- **Check:** Wing FTP service restart required
- **Check:** Cache invalidation (if using caching layer)

---

## 10. Files Generated

1. **access_control_system.py** - Core Python implementation
2. **organization_tree.json** - Hierarchical tree structure (JSON)
3. **wing_ftp_config.json** - Flat configuration for Wing FTP import
4. **IMPLEMENTATION_GUIDE.md** - This document

---

## 11. Next Steps

1. Review and customize the generated configurations
2. Set up test Wing FTP instance for validation
3. Customize Lua scripts or REST API integration based on your Wing FTP version
4. Plan user communication and training
5. Schedule production deployment

---

## Contact & Support

For questions about this implementation:
- Review Wing FTP Server documentation: https://www.wingftp.net/documentation
- Consult Wing FTP API reference for latest endpoints
- Consider engaging Wing FTP professional services for enterprise deployments

---

*Document Version: 1.0*  
*Last Updated: 2024*  
*Author: Senior Systems Architect*
