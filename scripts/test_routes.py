import requests

for page in ["keys.html", "usage.html", "invoices.html", "wallet.html", "rag.html", "playground.html", "admin-dashboard"]:
    print(f"Testing {page}...")
    try:
        r = requests.get(f"http://localhost:8080/{page}")
        print(f"  Status: {r.status_code}")
    except Exception as e:
        print(f"  Failed: {e}")
