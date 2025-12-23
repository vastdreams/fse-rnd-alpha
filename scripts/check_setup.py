"""Check if setup is complete and ready to run."""
import sys
from pathlib import Path

# Setup path - must be first
import _setup_path  # noqa: F401

from config.settings import get_settings
from src.db.connection import init_engine, check_database_health
from src.logging.logger import get_logger

logger = get_logger(__name__)


def check_setup():
    """Check if all prerequisites are met."""
    print("=" * 60)
    print("Checking Setup...")
    print("=" * 60)
    
    issues = []
    settings = None  # Initialize settings variable
    
    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        issues.append("❌ .env file not found")
    else:
        print("✅ .env file exists")
    
    # Check settings
    try:
        settings = get_settings()
        print(f"✅ Settings loaded")
        print(f"   - Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'configured'}")
        print(f"   - OpenAI API Key: {'✅ Set' if settings.OPENAI_API_KEY else '❌ Missing'}")
        print(f"   - SEC User Agent: {settings.SEC_USER_AGENT}")
    except Exception as e:
        issues.append(f"❌ Error loading settings: {e}")
        import traceback
        traceback.print_exc()  # Print full error for debugging
    
    # Check database connection (only if settings loaded)
    if settings:
        try:
            init_engine()
            health = check_database_health()
            if health.get("status") == "healthy":
                print("✅ Database connection successful")
            else:
                issues.append(f"❌ Database connection failed: {health.get('error')}")
        except Exception as e:
            issues.append(f"❌ Database connection error: {e}")
    
    # Check database tables
    try:
        from src.db.connection import db_session_scope
        from src.models.orm.company_year_core import CompanyYearCore
        
        with db_session_scope() as session:
            count = session.query(CompanyYearCore).count()
            if count > 0:
                print(f"✅ Database has data: {count} company years")
            else:
                print("⚠️  Database is empty - run pipeline first")
    except Exception as e:
        issues.append(f"❌ Error checking database: {e}")
    
    # Check required packages
    required_packages = [
        "flask",
        "dash",
        "sqlalchemy",
        "pandas",
        "numpy",
        "openai",
        "requests",
        "plotly",
    ]
    
    print("\nChecking Python packages...")
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} - not installed")
    
    if missing:
        issues.append(f"❌ Missing packages: {', '.join(missing)}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
    
    # Summary
    print("\n" + "=" * 60)
    if issues:
        print("❌ Setup Issues Found:")
        for issue in issues:
            print(f"   {issue}")
        print("\nFix issues above before running the app.")
        return False
    else:
        print("✅ Setup looks good! You can run the app.")
        print("\nNext steps:")
        print("1. If database is empty: python scripts/run_full_pipeline.py")
        print("2. Start server: python scripts/run_server.py")
        # Use settings that was already loaded, or reload if needed
        if not settings:
            settings = get_settings()
        print(f"3. Open browser: http://localhost:{settings.SERVER_PORT} (or check the port shown when server starts)")
        return True


if __name__ == "__main__":
    success = check_setup()
    sys.exit(0 if success else 1)

