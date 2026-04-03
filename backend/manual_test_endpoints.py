"""
Full test of all Person 1 backend endpoints + shift field registration.
"""
import requests, json

BASE = "http://localhost:8000/api/v1"

def test(label, method, url, body=None):
    try:
        if method == "POST":
            r = requests.post(url, json=body)
        else:
            r = requests.get(url)
        status = r.status_code
        data = r.json()
        ok = "PASS" if status in (200, 201) else "FAIL"
        print(f"  {ok}  [{status}] {label}")
        return data
    except Exception as e:
        print(f"  FAIL  {label} - {e}")
        return None

print("=" * 60)
print("PERSON 1 BACKEND - FULL TEST SUITE")
print("=" * 60)

# 1. Tiers
print("\n--- Tier Config ---")
d = test("GET /partners/tiers", "GET", f"{BASE}/partners/tiers")
if d:
    for t in ["flex", "standard", "pro"]:
        print(f"    {t}: Rs.{d[t]['weekly_premium']}/week, Rs.{d[t]['max_payout_day']}/day, {d[t]['max_days_week']} days")

# 2. RIQI all cities
print("\n--- RIQI All Cities ---")
d = test("GET /partners/riqi", "GET", f"{BASE}/partners/riqi")
if d:
    for city in d:
        print(f"    {city['city']}: RIQI={city['riqi_score']}, band={city['riqi_band']}, payout={city['payout_multiplier']}x")

# 3. RIQI single city
print("\n--- RIQI Bangalore ---")
d = test("GET /partners/riqi/bangalore", "GET", f"{BASE}/partners/riqi/bangalore")
if d:
    print(f"    {d['description']}")
    print(f"    {d['example']}")

# 4. Quotes
print("\n--- Premium Quotes (Bangalore, 20 active days) ---")
d = test("GET /partners/quotes", "GET", f"{BASE}/partners/quotes?city=bangalore&active_days_last_30=20")
if d:
    for q in d["quotes"]:
        print(f"    {q['tier']}: Rs.{q['weekly_premium']}/week (base Rs.{q['base_price']})")

# 5. BCR
print("\n--- BCR / Loss Ratio ---")
d = test("GET /partners/bcr/bangalore", "GET", f"{BASE}/partners/bcr/bangalore?total_claims_paid=5000&total_premiums_collected=8000")
if d:
    print(f"    BCR: {d['bcr']}, Loss ratio: {d['loss_ratio']}%, Status: {d['status']}")

# 6. Register with shift fields
print("\n--- Register with Shift Fields ---")
import random
phone = f"+91{random.randint(7000000000, 9999999999)}"
d = test("POST /partners/register", "POST", f"{BASE}/partners/register", body={
    "phone": phone,
    "name": "Test Partner",
    "platform": "zepto",
    "shift_days": ["mon", "tue", "wed", "thu", "fri"],
    "shift_start": "09:00",
    "shift_end": "18:00",
    "upi_id": "test@okaxis",
})
if d:
    print(f"    ID: {d['id']}, Name: {d['name']}")
    print(f"    shift_days: {d.get('shift_days')}")
    print(f"    shift_start: {d.get('shift_start')}")
    print(f"    shift_end: {d.get('shift_end')}")
    print(f"    zone_history: {d.get('zone_history')}")
    print(f"    upi_id: {d.get('upi_id')}")
    print(f"    kyc: {d.get('kyc')}")

# 7. Login + Update with shift fields
if d:
    print("\n--- Login + Update Shift Fields ---")
    login = test("POST /partners/login", "POST", f"{BASE}/partners/login", body={"phone": phone})
    if login and "otp" in login:
        verify = test("POST /partners/verify", "POST", f"{BASE}/partners/verify", body={"phone": phone, "otp": login["otp"]})
        if verify and "access_token" in verify:
            token = verify["access_token"]
            # Update shift
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            r = requests.patch(f"{BASE}/partners/me", json={
                "shift_days": ["sat", "sun"],
                "shift_start": "10:00",
                "shift_end": "16:00",
            }, headers=headers)
            updated = r.json()
            ok = "PASS" if r.status_code == 200 else "FAIL"
            print(f"  {ok}  [{r.status_code}] PATCH /partners/me (update shift)")
            print(f"    shift_days: {updated.get('shift_days')}")
            print(f"    shift_start: {updated.get('shift_start')}")
            print(f"    shift_end: {updated.get('shift_end')}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
