import json
import os

def main():
    compiled_json_path = "build/plugins.json"
    prebuilt_json_path = "prebuilt_plugins.json"
    
    compiled_plugins = []
    if os.path.exists(compiled_json_path):
        try:
            with open(compiled_json_path, "r", encoding="utf-8") as f:
                compiled_plugins = json.load(f)
        except Exception as e:
            print(f"Error loading compiled plugins.json: {e}")
            
    prebuilt_plugins = []
    if os.path.exists(prebuilt_json_path):
        try:
            with open(prebuilt_json_path, "r", encoding="utf-8") as f:
                prebuilt_plugins = json.load(f)
        except Exception as e:
            print(f"Error loading prebuilt_plugins.json: {e}")
            
    combined = {}
    for p in compiled_plugins:
        name = p.get("internalName") or p.get("name")
        if name:
            combined[name] = p
            
    for p in prebuilt_plugins:
        name = p.get("internalName") or p.get("name")
        if name:
            combined[name] = p
            
    try:
        os.makedirs(os.path.dirname(compiled_json_path), exist_ok=True)
        with open(compiled_json_path, "w", encoding="utf-8") as f:
            json.dump(list(combined.values()), f, indent=4, ensure_ascii=False)
        print(f"Successfully merged {len(compiled_plugins)} compiled and {len(prebuilt_plugins)} prebuilt plugins.")
    except Exception as e:
        print(f"Error writing merged plugins.json: {e}")

if __name__ == '__main__':
    main()
