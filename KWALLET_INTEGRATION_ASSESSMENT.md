# KWallet Integration Assessment for Katten API Key Storage

## Executive Summary

**Recommendation**: ✅ **PROCEED** with KWallet integration for this KDE Plasma-specific plugin.

KWallet is the **native, recommended** solution for secure credential storage in KDE environments. Given that Katten is specifically designed for KDE Plasma, KWallet integration provides optimal security and user experience.

---

## 1. Viability Analysis

### 1.1 KWallet Overview
- **Purpose**: KDE's secure password storage system
- **Encryption**: Blowfish encryption (AES-256 in newer versions)
- **Integration**: Native KDE service (kwalletd)
- **Standard Usage**: Used by browsers (Firefox, Chromium), email clients, and other KDE apps
- **Security**: Wallet is locked by default, unlocked with KDE session or master password

### 1.2 Compatibility with Katten
- ✅ **Target Platform**: KDE Plasma 6.3.6+ (as specified in requirements)
- ✅ **Native Integration**: KWallet is available on all KDE Plasma systems
- ✅ **Python Access**: Available via D-Bus or PyKDE4
- ✅ **User Expectations**: KDE users expect KWallet integration

### 1.3 Technical Feasibility
| Aspect | Status | Notes |
|--------|--------|-------|
| KWallet Availability | ✅ Available | Standard on KDE Plasma |
| Python Access | ✅ Available | Via dbus-python or PyKDE4 |
| D-Bus Interface | ✅ Stable | kwalletd provides D-Bus API |
| Encryption | ✅ Strong | Blowfish/AES-256 |
| Session Integration | ✅ Native | Unlocks with KDE session |

---

## 2. Implementation Considerations

### 2.1 Dependencies

#### Required
- `kwalletd` (KWallet daemon) - Already installed on KDE Plasma
- `dbus-python` or `pydbus` - For Python integration

#### Optional
- `PyKDE4` - Provides higher-level bindings (if available)

**Dependency Strategy**:
- Use **D-Bus** as primary method (most reliable, no extra Python packages needed)
- Graceful fallback to config.json if KWallet unavailable

### 2.2 Python Integration Methods

#### Option A: D-Bus Direct (Recommended)
```python
import dbus

# Connect to kwalletd
bus = dbus.SessionBus()
kwallet = bus.get_object('org.kde.kwalletd', '/modules/kwalletd')

# Open wallet
kwallet.Open('katten', 0, 'Katten')  # app_id, w_id, window_title
```

**Pros**:
- No extra Python packages required (dbus-python is typically pre-installed)
- Direct control over KWallet operations
- Works on all KDE systems

**Cons**:
- More verbose code
- Requires understanding of D-Bus API

#### Option B: PyKDE4 (If Available)
```python
from PyKDE4.kwallet import KWallet

wallet = KWallet.KWallet()
wallet.openWallet('katten', 0, 'Katten')
```

**Pros**:
- Higher-level, more Pythonic API
- Simpler code

**Cons**:
- Extra dependency (PyKDE4)
- May not be available on all systems

### 2.3 Wallet and Key Management

#### Wallet Structure
```
Wallet Name: "katten" (or reuse "Passwords")
Folder: "Katten" (optional, for organization)
Key: "mistral_api_key"
```

#### Operations Needed
1. **Read API Key**: Retrieve from KWallet
2. **Write API Key**: Store in KWallet
3. **Delete API Key**: Remove from KWallet
4. **Check Existence**: Verify if key exists
5. **Migration**: Import from config.json to KWallet

### 2.4 D-Bus API Reference

**Service**: `org.kde.kwalletd`  
**Object Path**: `/modules/kwalletd`  
**Interface**: `org.kde.KWallet`

**Key Methods**:
- `Open(wallet, w_id, window_title)` - Open wallet
- `Close(wallet, w_id)` - Close wallet
- `ReadPassword(wallet, key, w_id)` - Read password
- `WritePassword(wallet, key, password, w_id)` - Write password
- `RemoveEntry(wallet, key, w_id)` - Remove entry
- `HasEntry(wallet, key, w_id)` - Check if entry exists

**Note**: `w_id` is window ID (can be 0 for CLI apps)

---

## 3. Implementation Plan

### 3.1 Phase 1: Core Integration

**Files to Modify**:
1. `katten.py` - Main API key retrieval logic
2. `katten-config.py` - Configuration tool
3. `first_run_panel.py` - First-run panel

**New Functions Needed**:

```python
class KWalletManager:
    """Manage API key storage in KWallet."""
    
    def __init__(self):
        self.bus = dbus.SessionBus()
        self.kwallet = None
        self.wallet_name = "katten"
        self.wallet_open = False
    
    def open_wallet(self):
        """Open the KWallet wallet."""
        try:
            kwallet = self.bus.get_object('org.kde.kwalletd', '/modules/kwalletd')
            interface = dbus.Interface(kwallet, 'org.kde.KWallet')
            interface.Open(self.wallet_name, 0, 'Katten')  # w_id=0 for CLI
            self.wallet_open = True
            return True
        except Exception as e:
            logging.warning(f"Failed to open KWallet: {e}")
            return False
    
    def read_api_key(self):
        """Read API key from KWallet."""
        if not self.wallet_open:
            if not self.open_wallet():
                return None
        try:
            kwallet = self.bus.get_object('org.kde.kwalletd', '/modules/kwalletd')
            interface = dbus.Interface(kwallet, 'org.kde.KWallet')
            return interface.ReadPassword(self.wallet_name, "mistral_api_key", 0)
        except Exception as e:
            logging.warning(f"Failed to read from KWallet: {e}")
            return None
    
    def write_api_key(self, api_key):
        """Write API key to KWallet."""
        if not self.wallet_open:
            if not self.open_wallet():
                return False
        try:
            kwallet = self.bus.get_object('org.kde.kwalletd', '/modules/kwalletd')
            interface = dbus.Interface(kwallet, 'org.kde.KWallet')
            interface.WritePassword(self.wallet_name, "mistral_api_key", api_key, 0)
            return True
        except Exception as e:
            logging.warning(f"Failed to write to KWallet: {e}")
            return False
    
    def close_wallet(self):
        """Close the KWallet wallet."""
        if self.wallet_open:
            try:
                kwallet = self.bus.get_object('org.kde.kwalletd', '/modules/kwalletd')
                interface = dbus.Interface(kwallet, 'org.kde.KWallet')
                interface.Close(self.wallet_name, 0)
                self.wallet_open = False
            except Exception:
                pass
```

### 3.2 Phase 2: Migration Strategy

**Automatic Migration**:
```python
def migrate_to_kwallet():
    """Migrate API key from config.json to KWallet."""
    config = load_config()
    api_key = config.get("api_key")
    
    if api_key:
        kwallet = KWalletManager()
        if kwallet.write_api_key(api_key):
            # Remove from config file
            config["api_key"] = ""
            save_config(config)
            return True
    return False
```

**Migration Triggers**:
- On first run after KWallet integration
- When user opens config panel
- Manual migration command

### 3.3 Phase 3: Fallback Strategy

**Priority Order**:
1. KWallet (if available and unlocked)
2. Environment variable (`MISTRAL_API_KEY`)
3. Config file (`~/.config/katten/config.json`)
4. No API key (error message)

```python
def get_api_key():
    """Get API key with fallback strategy."""
    # Try KWallet first
    kwallet = KWalletManager()
    api_key = kwallet.read_api_key()
    if api_key:
        return api_key
    
    # Fallback to environment variable
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if api_key:
        return api_key
    
    # Fallback to config file
    config = load_config()
    return config.get("api_key", "")
```

---

## 4. Security Considerations

### 4.1 Advantages Over Current Approach

| Aspect | Current (Config File) | KWallet | Improvement |
|--------|----------------------|--------|-------------|
| Encryption at rest | ❌ None | ✅ Blowfish/AES-256 | 🟢 Significant |
| Memory protection | ❌ Plain text | ✅ Encrypted | 🟢 Significant |
| Access control | ❌ File permissions only | ✅ Wallet lock + file permissions | 🟢 Moderate |
| Session integration | ❌ None | ✅ Unlocks with KDE session | 🟢 Significant |
| Backup safety | ❌ Key in backups | ✅ Wallet excluded from backups by default | 🟢 Moderate |

### 4.2 Potential Security Issues

**Mitigation Strategies**:

1. **KWallet Not Running**:
   - Fallback to config file gracefully
   - Log warning but continue operation

2. **Wallet Locked**:
   - KWallet automatically prompts user to unlock
   - Application blocks until unlocked or cancelled

3. **D-Bus Permission Issues**:
   - KWallet runs as user service
   - Same user can access own wallet

4. **Key Leakage**:
   - Ensure API key is never logged
   - Clear from memory when not needed (optional)

---

## 5. User Experience Considerations

### 5.1 First-Time Setup
- User runs plugin or config tool
- If KWallet not configured: Prompt to configure
- If KWallet locked: Automatic unlock prompt from KDE
- If migration needed: Automatic migration from config.json

### 5.2 Existing Users
- **Automatic migration**: On first run after update
- **Fallback**: If migration fails, continue using config.json
- **Notification**: Inform user that API key is now stored more securely

### 5.3 Configuration Tool
- Add KWallet toggle option
- Allow users to choose between KWallet and config file
- Provide migration button

### 5.4 Error Scenarios
- **KWallet not installed**: Fallback to config file, show warning
- **Wallet access denied**: Clear error message with fallback option
- **Migration failure**: Keep both copies, warn user

---

## 6. Cross-Platform Considerations

### 6.1 KDE Plasma Only
- **KWallet**: Available on all KDE Plasma installations
- **D-Bus**: Standard on Linux desktops
- **Fallback**: Config file always available

### 6.2 Non-KDE Environments
- **KWallet may not be available**: Fallback to config file
- **Graceful degradation**: Plugin continues to work
- **Clear messaging**: User informed about missing KWallet

---

## 7. Implementation Complexity

| Component | Complexity | Estimated Time |
|-----------|------------|----------------|
| KWallet D-Bus wrapper | Low | 1-2 hours |
| API key retrieval modification | Low | 1 hour |
| Config tool modification | Medium | 2-3 hours |
| First-run panel modification | Medium | 2-3 hours |
| Migration logic | Medium | 2 hours |
| Testing | Medium | 2-3 hours |
| **Total** | **Medium** | **8-12 hours** |

---

## 8. Testing Requirements

### 8.1 Test Cases Needed
1. ✅ KWallet available and unlocked
2. ✅ KWallet available but locked
3. ✅ KWallet not available (fallback to config file)
4. ✅ Migration from config.json to KWallet
5. ✅ Migration when config.json doesn't exist
6. ✅ Multiple API key operations
7. ✅ Concurrent access
8. ✅ Wallet doesn't exist yet
9. ✅ Permission errors
10. ✅ Environment variable override

### 8.2 Test Environments
- KDE Plasma 6.3.6+
- KWallet configured
- KWallet not configured
- Different KDE themes
- Fresh system (no existing config)

---

## 9. Risk Assessment

### 9.1 Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| D-Bus connection failure | Low | Medium | Graceful fallback |
| KWallet API changes | Very Low | Medium | Version detection |
| Performance impact | Very Low | Low | None needed |
| Memory leaks | Low | Low | Proper cleanup |
| Data corruption | Very Low | Medium | Validation checks |

### 9.2 User Experience Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Confusing migration | Medium | Medium | Clear messaging |
| Locked wallet frustration | Medium | Medium | Auto-unlock prompt |
| Breaking existing workflows | Low | High | Thorough testing |

---

## 10. Recommendation and Next Steps

### ✅ PROCEED with Implementation

**Rationale**:
1. **Native KDE solution**: Perfect fit for KDE Plasma plugin
2. **Significant security improvement**: Encryption at rest vs plain text
3. **Expected by users**: KDE users expect KWallet integration
4. **Manageable complexity**: Implementation is straightforward with D-Bus
5. **Graceful fallback**: Existing functionality preserved

### 📋 Implementation Priority

1. **High Priority**: Core KWallet integration in `katten.py`
2. **High Priority**: Configuration tool updates
3. **Medium Priority**: First-run panel updates
4. **Medium Priority**: Migration logic
5. **Low Priority**: Advanced features (key deletion, multiple keys)

### 🎯 Next Actions

1. **Create implementation branch** ✅ (already done: `feature/kwallet-integration`)
2. **Implement KWalletManager class** using D-Bus
3. **Modify get_api_key()** to use KWallet with fallback
4. **Update configuration tools**
5. **Implement migration logic**
6. **Add comprehensive tests**
7. **User testing and feedback**

### 📊 Success Metrics

- [ ] API key successfully stored in KWallet
- [ ] API key successfully retrieved from KWallet
- [ ] Graceful fallback to config file when KWallet unavailable
- [ ] Automatic migration from config.json to KWallet
- [ ] No breaking changes for existing users
- [ ] Clear error messages and user guidance

---

## Appendix A: D-Bus API Reference

### Service: org.kde.kwalletd

**Methods**:
```
Open(string wallet, uint w_id, string window_title) -> bool
Close(string wallet, uint w_id) -> bool
ReadPassword(string wallet, string key, uint w_id) -> string
WritePassword(string wallet, string key, string password, uint w_id) -> bool
RemoveEntry(string wallet, string key, uint w_id) -> bool
HasEntry(string wallet, string key, uint w_id) -> bool
ListFolders(string wallet, uint w_id) -> array of string
ListEntries(string wallet, string folder, uint w_id) -> array of string
```

**Signals**:
```
WalletCreated(string wallet)
WalletRemoved(string wallet)
```

---

## Appendix B: KWallet Configuration Files

KWallet configuration is stored in:
- `~/.config/kwalletrc` - Global KWallet configuration
- `~/.local/share/kwalletd/` - Wallet files (encrypted)

---

*Document created: 2026-06-06*  
*Author: Mistral Vibe*