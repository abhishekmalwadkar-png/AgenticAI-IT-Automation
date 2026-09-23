"""
Production Bootstrap & Self-Healing Dependency Manager
Automatically verifies and manages runtime dependencies for production readiness.
"""

import sys
import subprocess
import importlib
import logging

logger = logging.getLogger("Bootstrap")

# Critical core dependencies required for server operation
CRITICAL_PACKAGES = {
    "fastapi": "fastapi>=0.100.0",
    "uvicorn": "uvicorn[standard]>=0.23.0",
    "pydantic": "pydantic>=2.0.0",
    "dotenv": "python-dotenv>=1.0.0",
    "requests": "requests>=2.31.0",
}

def install_package(pkg_spec: str) -> bool:
    """Attempts to install a package using pip with fallback to --user."""
    logger.info(f"Auto-installing dependency: {pkg_spec}")
    try:
        cmd = [sys.executable, "-m", "pip", "install", "--no-warn-script-location", pkg_spec]
        subprocess.check_call(cmd, timeout=45)
        logger.info(f"Successfully installed '{pkg_spec}'")
        return True
    except Exception as e:
        logger.warning(f"Standard install for '{pkg_spec}' failed: {e}. Retrying with --user...")
        try:
            cmd_user = [sys.executable, "-m", "pip", "install", "--user", "--no-warn-script-location", pkg_spec]
            subprocess.check_call(cmd_user, timeout=45)
            logger.info(f"Successfully installed '{pkg_spec}' via --user.")
            return True
        except Exception as ex:
            logger.error(f"Could not install '{pkg_spec}': {ex}")
            return False

def verify_critical_dependencies():
    """
    Fast, non-blocking check on server startup.
    Auto-installs any missing critical web/API dependencies.
    """
    for module_name, pkg_spec in CRITICAL_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            logger.warning(f"Critical module '{module_name}' missing. Auto-installing {pkg_spec}...")
            install_package(pkg_spec)
        except Exception:
            pass

# Perform fast critical check on load
verify_critical_dependencies()
