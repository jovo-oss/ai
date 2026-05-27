import sys
import os
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

print("=" * 60)
print("Starting AI Chat System Server")
print("=" * 60)

try:
    print("\n[1/5] Loading environment...")
    from dotenv import load_dotenv
    load_dotenv()
    print("   OK")
    
    print("\n[2/5] Initializing database...")
    from app.models.database import init_db
    init_db()
    print("   OK")
    
    print("\n[3/5] Loading plugins...")
    from app.plugins.plugin_base import plugin_manager
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plugins_dir = os.path.join(project_root, "plugins")
    print(f"   Plugin dir: {plugins_dir}")
    plugin_manager.load_plugins_from_directory(plugins_dir)
    print("   OK")
    
    print("\n[4/5] Loading routes...")
    from app.routes import chat, plugins, models, characters, worldbook, configs, voice_configs, agent, alarm_reminders, environment, proactive_interaction
    print("   OK")
    
    print("\n[5/5] Loading services...")
    from app.services.alarm_scheduler import alarm_scheduler
    from app.services.proactive_interaction_service import proactive_interaction_service
    print("   OK")
    
    print("\n[6/6] Creating FastAPI app...")
    from app.main import app
    print("   OK")
    
    print("\n" + "=" * 60)
    print("All modules loaded successfully!")
    print("=" * 60)
    
    print("\nStarting server on http://127.0.0.1:8000...")
    print("Press Ctrl+C to stop\n")
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    
except KeyboardInterrupt:
    print("\nServer stopped by user")
except Exception as e:
    print(f"\n{'=' * 60}")
    print(f"ERROR: {e}")
    print(f"{'=' * 60}")
    traceback.print_exc()
    input("\nPress Enter to exit...")
