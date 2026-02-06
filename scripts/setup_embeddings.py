"""
Quick script to help set up Google API key for fast embeddings
"""

import os
from pathlib import Path

def setup_google_api_key():
    """Interactive setup for Google API key"""
    
    print("="*70)
    print("🚀 Fast Embeddings Setup - Google Gemini API")
    print("="*70)
    
    print("\n📌 Why Google Gemini?")
    print("   • 100x faster than local Ollama (2 mins vs 30+ mins)")
    print("   • FREE for standard usage")
    print("   • High quality embeddings")
    print("   • Automatic fallback to Ollama if unavailable")
    
    print("\n" + "="*70)
    print("Step 1: Get Your Free API Key")
    print("="*70)
    print("\n1. Open this URL in your browser:")
    print("   👉 https://aistudio.google.com/app/apikey")
    print("\n2. Sign in with Google account")
    print("3. Click 'Create API Key'")
    print("4. Copy the key (starts with 'AIza...')")
    
    input("\nPress ENTER when you have your API key ready...")
    
    api_key = input("\nPaste your Google API key here: ").strip()
    
    if not api_key:
        print("\n❌ No API key provided. Using local Ollama instead.")
        return False
    
    if not api_key.startswith("AIza"):
        print("\n⚠️  Warning: Key doesn't start with 'AIza'. Are you sure this is correct?")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return False
    
    # Update .env file
    env_path = Path(".env")
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update or add GOOGLE_API_KEY
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("GOOGLE_API_KEY="):
                lines[i] = f'GOOGLE_API_KEY="{api_key}"\n'
                updated = True
                break
        
        if not updated:
            lines.insert(0, f'GOOGLE_API_KEY="{api_key}"\n')
        
        with open(env_path, 'w') as f:
            f.writelines(lines)
    else:
        # Create new .env file
        with open(env_path, 'w') as f:
            f.write(f'GOOGLE_API_KEY="{api_key}"\n')
    
    print("\n✅ API key saved to .env file!")
    print("\n" + "="*70)
    print("Step 2: Build Vector Store")
    print("="*70)
    print("\nRun this command:")
    print("   python src/pdf_processor.py")
    print("\nChoose option 1 (Google Gemini) when prompted.")
    print("\n" + "="*70)
    
    return True


if __name__ == "__main__":
    try:
        setup_google_api_key()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
