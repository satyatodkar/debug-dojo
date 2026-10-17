import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(url, key)

response = supabase.table("submissions").insert({
    "learner_id": "student1",
    "challenge_id": 9,
    "code": "def sum_positive_numbers(numbers):\n    return sum(n for n in numbers if n > 0)",
    "status": "passed",
    "tests_passed": 3,
    "tests_total": 3
}).execute()

print("Record inserted successfully:", response.data)
