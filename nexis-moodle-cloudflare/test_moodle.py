import requests
H = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"}
r = requests.get("https://moodle.alaqsa.edu.ps/login/index.php", headers=H, timeout=20)
print(r.status_code, r.headers.get("server"), "Just a moment" in r.text)
