import os
from dotenv import load_dotenv
from supabase import create_client
from challenges import CHALLENGES

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

records = []
for ch in CHALLENGES:
    records.append({
        "id": str(ch.get("id")),
        "title": ch.get("title", ""),
        "difficulty": ch.get("difficulty", "EASY"),
        "starter_code": ch.get("buggy_code") or ch.get("starter_code") or "",
        "description": ch.get("description", "")
    })

res = supabase.table("challenges").upsert(records).execute()
print(f"Challenges sync aagide! Total: {len(res.data)}")
