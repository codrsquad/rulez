from pathlib import Path
import sys
import tomllib as toml
import codemod_yaml

with open(Path(__file__).parent / "upgrade.toml", "rb") as f:
    latest_versions = toml.load(f)

def fix(path):
    stream = codemod_yaml.parse(path.read_bytes())
    for job_name in stream["jobs"]:
        for step in stream["jobs"][job_name]["steps"]:
            key = step.get("uses", "").split("@")[0]
            if key in latest_versions:
                desired = f"{key}@{latest_versions[key]}"
                if step["uses"] != desired:
                    step["uses"] = desired

    path.write_bytes(stream.text)
        
        
    
if __name__ == "__main__":
    for f in sys.argv[1:]:
        fix(Path(f))
