# Known Issues - First Run Panel

This document details persisting issues that have been identified but not yet resolved, along with comprehensive information about attempted solutions to avoid duplicate work.

---

## Issue #1: Multiple Panel Instances Still Appearing

### Description
When triggering the KRunner plugin multiple times in quick succession, multiple instances of the first-run configuration panel can still appear, despite implementing various singleton and locking mechanisms.

### Impact
- User experience degraded by duplicate panels
- Potential resource waste
- Confusing user interface

### Attempted Solutions

#### 1. Class-Level Singleton Pattern
**Implementation:**
```python
class FirstRunPanel(QDialog):
    _instance = None
    
    def __init__(self):
        if FirstRunPanel._instance is not None:
            existing = FirstRunPanel._instance
            existing.raise_()
            existing.activateWindow()
            return
        # ... rest of init
        FirstRunPanel._instance = self
```

**Result:** ❌ Failed - Works within same process but KRunner creates new processes

#### 2. Function-Level Singleton Check
**Implementation:**
```python
def show_first_run_panel():
    if FirstRunPanel._instance is not None:
        existing = FirstRunPanel._instance
        existing.raise_()
        existing.activateWindow()
        return False
    panel = FirstRunPanel()
    # ...
```

**Result:** ❌ Failed - Still allows multiple instances across processes

#### 3. File-Based Cross-Process Locking
**Implementation:**
```python
LOCK_FILE = Path.home() / ".config" / "katten" / "first_run_panel.lock"

def _create_lock_file():
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, 'w') as f:
        f.write(str(time.time()))

def _remove_lock_file():
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass

def _is_panel_running():
    return LOCK_FILE.exists()
```

**Integration:**
- Called `_create_lock_file()` in `__init__`
- Called `_remove_lock_file()` in `closeEvent`
- Checked `_is_panel_running()` at start of `show_first_run_panel()`

**Result:** ❌ Failed - Still allows multiple instances

### Hypothesis for Persisting Issue

**Root Cause:** KRunner plugin architecture may be creating completely isolated processes where:
1. Each plugin invocation spawns a new process with its own Python interpreter
2. Class variables are not shared between processes
3. File locking may have race conditions or timing issues
4. KRunner may be launching multiple plugin instances simultaneously before the lock file is created

### Recommended Next Steps

1. **Investigate KRunner Plugin Architecture**
   - Determine exactly how KRunner launches plugin processes
   - Check if there's a standard way for KRunner plugins to prevent multiple instances

2. **Implement More Robust IPC**
   - Use D-Bus service activation (standard on Linux/KDE)
   - Implement socket-based communication between instances
   - Use systemd or other service manager if applicable

3. **Check Timing Issues**
   - Add logging to debug when lock files are created/removed
   - Test with deliberate delays to identify race conditions

4. **KRunner-Specific Solution**
   - Investigate if KRunner provides APIs for plugin instance management
   - Check how other KRunner plugins handle this issue

---

## Issue #3: Theme Typography Not Reflected

### Description
Text elements in the first-run panel do not properly reflect the user's custom theme typography settings, despite using pure Qt methods and application fonts.

### Impact
- Inconsistent visual appearance with system theme
- Poor integration with KDE Plasma customization
- Non-native look and feel

### Attempted Solutions

#### 1. Application Font Inheritance
**Implementation:**
```python
app = QApplication.instance()
if app:
    self._base_font = app.font()
else:
    temp_app = QApplication(sys.argv)
    self._base_font = temp_app.font()
    temp_app.quit()
```

**Result:** ❌ Failed - Fonts still don't match theme

#### 2. Creating Font Copies
**Implementation:**
```python
# For all custom fonts:
title_font = QFont(self._base_font)  # Create a copy
title_font.setBold(True)
title_font.setPointSize(title_font.pointSize() + 4)
```

**Result:** ❌ Failed - Fonts still don't match theme

#### 3. Using System Font Directly
**Implementation:**
```python
# Tried using QFont() without modification
# Tried using system font explicitly
```

**Result:** ❌ Failed - Still inconsistent with theme

### Hypothesis for Persisting Issue

**Root Cause:** The issue may be one of the following:

1. **QApplication Context**: The first-run panel may be running in a different QApplication context than the main Plasma session, so `app.font()` returns a different font than expected.

2. **Font Loading Timing**: The system fonts may not be fully loaded when the panel is created, especially if it's triggered early in the session.

3. **KDE Theme System**: The panel may not be properly integrating with KDE's theme system (KWin, Plasma, etc.).

4. **Qt Style Sheet Overrides**: There may be global Qt style sheets or KDE configuration that affects font rendering.

### Recommended Next Steps

1. **Debug Font Information**
   - Add logging to output the actual font family, size, weight being used
   - Compare with expected theme fonts

2. **Test in Isolation**
   - Create a minimal test application that just shows a QLabel with theme font
   - Verify that Qt theme integration works outside of KRunner context

3. **Investigate KDE Integration**
   - Check if QApplication needs special setup for KDE themes
   - Verify that the correct Qt style plugin (e.g., "breeze", "kvantum") is being used

4. **Force Theme Application**
   - Explicitly set the application font to the system font
   - Use QStyleFactory to ensure correct style is loaded

5. **Environment Inspection**
   - Check environment variables (QT_STYLE_OVERRIDE, QT_FONT_DPI, etc.)
   - Verify that the panel is running in the correct graphical environment

---

## General Recommendations

1. **Logging**: Add comprehensive logging to both issues to gather more diagnostic information
2. **Minimal Test Cases**: Create minimal reproducible test cases for each issue
3. **KDE Documentation**: Consult KRunner plugin development documentation for best practices
4. **Community Resources**: Check KDE development forums and mailing lists for similar issues
5. **Existing Plugins**: Study how established KRunner plugins handle these scenarios

---

*Last updated: 2026-06-06*
*Document created by: Mistral Vibe*