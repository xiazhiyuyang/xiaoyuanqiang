"""后端全流程冒烟测试：敏感词/私信/举报/微信登录。用标准库，跑完自动清理。"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8011"
PASS, FAIL = 0, 0


def call(method, path, token=None, body=None, expect_code=0, expect_http=200):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        status = e.code
        payload = json.loads(e.read().decode())
    ok = status == expect_http and (payload.get("code") == expect_code if expect_http == 200 else True)
    print(f"[{'OK ' if ok else 'BAD'}] {method} {path} -> http={status} code={payload.get('code')} msg={payload.get('msg') or payload.get('detail')}")
    if not ok:
        print("     payload:", json.dumps(payload, ensure_ascii=False)[:300])
    global PASS, FAIL
    PASS += int(ok)
    FAIL += int(not ok)
    return payload


def main():
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/campus_smoke.db"
    env["SECRET_KEY"] = "test-secret"
    env["DEBUG"] = "False"
    if os.path.exists("/tmp/campus_smoke.db"):
        os.remove("/tmp/campus_smoke.db")

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8011", "--log-level", "warning"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.dirname(__file__) or ".",
    )
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(BASE + "/api/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            print("SERVER START FAILED")
            print(proc.stdout.read().decode()[-2000:])
            return 1

        print("== 注册/登录 ==")
        alice = call("POST", "/api/auth/register", body={
            "username": "alice01", "password": "pass123456", "nickname": "爱丽丝"}).get("data", {})
        bob = call("POST", "/api/auth/register", body={
            "username": "bob02", "password": "pass123456", "nickname": "鲍勃"}).get("data", {})
        admin = call("POST", "/api/auth/login", body={"username": "admin", "password": "admin123456"}).get("data", {})
        ta, tb, tadmin = alice.get("access_token"), bob.get("access_token"), admin.get("access_token")

        print("== 敏感词：mask / block ==")
        p1 = call("POST", "/api/posts", token=ta, body={
            "title": "问个问题", "content": "楼下那人真是傻逼啊", "is_anonymous": False})
        assert "**" in (p1.get("data", {}).get("content") or ""), "mask 未生效"
        print("     mask 结果:", p1["data"]["content"])
        call("POST", "/api/posts", token=ta, body={
            "title": "兼职", "content": "想赚钱的加微信 vx123"}, expect_http=400)
        c1 = call("POST", f"/api/posts/{p1['data']['id']}/comments", token=tb,
                  body={"content": "楼上煞笔吧"})
        print("     评论 mask 结果:", c1["data"]["content"])

        print("== 私信 ==")
        conv = call("POST", "/api/messages/conversations", token=ta,
                    body={"target_user_id": bob["user"]["id"]}).get("data", {})
        cid = conv.get("id")
        call("POST", f"/api/messages/conversations/{cid}/messages", token=ta,
             body={"content": "你好呀鲍勃"})
        call("POST", f"/api/messages/conversations/{cid}/messages", token=ta,
             body={"content": "在吗？兼职刷单了解下"}, expect_http=400)
        call("POST", f"/api/messages/conversations/{cid}/messages", token=tb,
             body={"content": "在的，怎么了"})
        uc = call("GET", "/api/messages/unread-count", token=tb)
        assert uc["data"]["count"] == 1, f"bob 未读应为1，实际{uc['data']}"
        msgs = call("GET", f"/api/messages/conversations/{cid}/messages", token=tb)
        assert len(msgs["data"]["items"]) == 2, "消息数应为2"
        uc2 = call("GET", "/api/messages/unread-count", token=tb)
        assert uc2["data"]["count"] == 0, "读过后未读应为0"
        convs = call("GET", "/api/messages/conversations", token=ta)
        assert convs["data"][0]["last_content"] == "在的，怎么了"
        print("     会话列表最后一条:", convs["data"][0]["last_content"])

        print("== 举报与审核 ==")
        r = call("POST", "/api/reports", token=tb, body={
            "target_type": "post", "target_id": p1["data"]["id"],
            "reason": "abuse", "detail": "评论区骂人"})
        call("POST", "/api/reports", token=tb, body={
            "target_type": "post", "target_id": p1["data"]["id"], "reason": "other"}, expect_http=400)
        rl = call("GET", "/api/admin/reports?status=pending", token=tadmin)
        assert rl["data"]["total"] >= 1
        rid = rl["data"]["items"][0]["id"]
        call("POST", f"/api/admin/reports/{rid}/handle", token=tadmin,
             body={"status": "approved", "ban_user": False})
        gone = call("GET", f"/api/posts/{p1['data']['id']}", expect_http=404)
        print("     举报通过后帖子:", gone.get("detail"))

        print("== 敏感词管理 ==")
        wl = call("GET", "/api/admin/sensitive-words", token=tadmin)
        print("     默认词库数量:", wl["data"]["total"])
        call("POST", "/api/admin/sensitive-words", token=tadmin,
             body={"word": "测试违禁词xyz", "category": "other", "action": "block"})
        bi = call("POST", "/api/admin/sensitive-words/batch", token=tadmin,
                  body={"text": "批量词A\n批量词B\n批量词A", "action": "mask"})
        print("    ", bi["msg"])
        # 新 block 词应立即生效
        call("POST", "/api/posts", token=ta, body={"title": "测试违禁词xyz出现", "content": "正常"},
             expect_http=400)

        print("== 微信登录（未配置应 503）==")
        call("POST", "/api/auth/wechat", body={"code": "fake-code"}, expect_http=503)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        if os.path.exists("/tmp/campus_smoke.db"):
            os.remove("/tmp/campus_smoke.db")

    print(f"\n结果：{PASS} 通过，{FAIL} 失败")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
