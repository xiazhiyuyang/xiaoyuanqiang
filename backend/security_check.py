import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
passed = failed = 0


def hdr(h, name):
    name = name.lower()
    for k, v in h.items():
        if k.lower() == name:
            return v
    return None


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"[OK ] {name} {detail}")
    else:
        failed += 1
        print(f"[FAIL] {name} {detail}")


def req(method, path, body=None, token=None, headers=None, raw=None):
    url = BASE + path
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    if headers:
        h.update(headers)
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


def login(username, password):
    s, _, b = req("POST", "/api/auth/login", {"username": username, "password": password})
    if s == 200:
        return json.loads(b)["data"]["access_token"]
    return None


# 1. 安全响应头
s, h, _ = req("GET", "/api/posts")
check("安全头 X-Frame-Options", hdr(h, "X-Frame-Options") == "DENY", h.get("X-Frame-Options", ""))
check("安全头 X-Content-Type-Options", hdr(h, "X-Content-Type-Options") == "nosniff")
rp = hdr(h, "Referrer-Policy") or ""
check("安全头 Referrer-Policy", rp in ("strict-origin-when-cross-origin", "no-referrer"), rp)
check("安全头 CSP 存在", any(k.lower()=="content-security-policy" for k in h))

# 2. 生产关闭 docs
s, _, _ = req("GET", "/docs")
check("生产环境 /docs 关闭", s in (404, 403), f"http={s}")

# 3. 弱密码注册被拒
s, _, b = req("POST", "/api/auth/register",
              {"username": "weakpw_test", "password": "123", "nickname": "弱密码"})
check("弱密码注册拒绝", s == 422, f"http={s}")
s, _, _ = req("POST", "/api/auth/register",
              {"username": "weakpw_test2", "password": "12345678", "nickname": "纯数字"})
check("纯数字密码拒绝", s == 422, f"http={s}")

# 4. 越权访问他人私信会话
t1 = login("demo1", "demo123456")
# 注册一个与会话完全无关的第三方用户
import random
uname = "third" + str(random.randint(10000, 99999))
s, _, _ = req("POST", "/api/auth/register",
              {"username": uname, "password": "third123456", "nickname": "路人甲"})
t3 = login(uname, "third123456")
s, _, b = req("GET", "/api/messages/conversations", token=t1)
d = json.loads(b)["data"]; conv1 = d["items"] if isinstance(d, dict) else d
if conv1 and t3:
    cid = conv1[0]["id"]
    s2, _, _ = req("GET", f"/api/messages/conversations/{cid}/messages", token=t3)
    check("第三方越权读取他人私信拒绝", s2 in (403, 404), f"http={s2}")
else:
    check("第三方越权读取他人私信拒绝", False, "(前置失败)")

# 5. 伪造图片上传：png 头是假的文本
fake_png = b"\x89PNG\r\n\x1a\n" + b"this is not a real image" + b"\x00" * 30
boundary = "----secboundary"
body = (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="file"; filename="fake.png"\r\n'
    "Content-Type: image/png\r\n\r\n"
).encode() + fake_png + f"\r\n--{boundary}--\r\n".encode()
s, _, b = req("POST", "/api/upload/image", raw=body, token=t1,
              headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
check("伪造图片上传拒绝", s in (400, 422), f"http={s} {b[:80]}")

# 6. CORS 白名单：恶意 Origin 不被允许
s, h, _ = req("GET", "/api/posts", headers={"Origin": "https://evil.example.com"})
acao = hdr(h, "Access-Control-Allow-Origin") or "<none>"
check("恶意 Origin 不放行 CORS", not hdr(h, "Access-Control-Allow-Origin"), f"acao={acao}")

# 7. 登录限流：连续 11 次错误密码（阈值 10/分）
last = None
for i in range(12):
    s, _, _ = req("POST", "/api/auth/login",
                  {"username": "demo1", "password": f"wrong{i}xxxx"})
    last = s
check("登录爆破触发限流 429", last == 429, f"last_http={last}")

print(f"\n结果：{passed} 通过，{failed} 失败")
