"""生成演示数据：5 个用户、8 个帖子、评论、1 条待处理举报、1 个私信会话。
演示账号密码均为 demo123456，管理员 admin/admin123456。"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///" + os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "preview.db")
    ),
)
os.environ.setdefault("SECRET_KEY", "preview-secret")

from sqlalchemy import select, delete
from app.database import init_db, AsyncSessionLocal
from app.main import init_default_data
from app.core.security import hash_password
from app.models.user import User
from app.models.post import Post, Category
from app.models.comment import Comment
from app.models.report import Report
from app.models.message import Conversation, Message


def ago(hours: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        await init_default_data()
        # 清掉旧演示数据，保证可重复执行
        for model in (Message, Conversation, Report, Comment, Post, User):
            await db.execute(delete(model).where(model.id > 0))
        # admin 被删了，重建
        db.add(User(username="admin", nickname="管理员",
                    password_hash=hash_password("admin123456"), role="admin"))
        await db.commit()

        users = [
            User(username="demo1", nickname="小明", password_hash=hash_password("demo123456"),
                 bio="今天也要加油鸭"),
            User(username="demo2", nickname="奶茶不加冰", password_hash=hash_password("demo123456"),
                 bio="三分糖谢谢"),
            User(username="demo3", nickname="图书馆常驻", password_hash=hash_password("demo123456")),
            User(username="demo4", nickname="夜跑达人", password_hash=hash_password("demo123456")),
            User(username="demo5", nickname="校园咸鱼", password_hash=hash_password("demo123456")),
        ]
        db.add_all(users)
        await db.commit()
        for u in users:
            await db.refresh(u)

        cats = {c.slug: c for c in (await db.execute(select(Category))).scalars().all()}

        posts_data = [
            # (作者idx, 分类, 标题, 正文, 匿名, 几小时前, 浏览, 赞, 评)
            (0, "confession", "三食堂二楼的白裙女生",
             "连续一周在三食堂二楼遇到你了，总是坐靠窗的位置，扎马尾穿白裙子。每次想上前打招呼都鼓不起勇气……如果你也刷校园墙，能不能明天中午还坐那个位置，我想请你喝杯奶茶。",
             True, 3, 1286, 87, 12),
            (1, "rant", "早八为什么还要签到啊",
             "八点的课本来就起不来，到了教室还要扫码签到+定位+人脸三连，迟到一分钟直接算缺勤。老师是觉得我们会为了不签到直接睡过头吗？？",
             False, 5, 892, 45, 23),
            (2, "question", "图书馆三楼哪里还有插座",
             "期末周插座全靠抢，请问三楼靠窗那排哪个位置插座是好的？昨天搬着电脑换了三个位置都没电，人麻了。",
             False, 8, 421, 12, 8),
            (4, "market", "出二手自行车一辆 80 元",
             "毕业出一辆山地自行车，变速正常，刹车刚换，骑了两年没啥毛病，80 元自取，坐标 7 栋楼下，有意私信。",
             False, 10, 356, 5, 6),
            (3, "lostfound", "丢了一串带小熊挂件的钥匙",
             "昨天下午在操场到二食堂的路上丢了一串钥匙，上面有个棕色小熊挂件，对我很重要，捡到的同学请联系我，请你喝奶茶！",
             False, 26, 267, 9, 4),
            (0, "chat", "今晚操场有人夜跑吗",
             "一个人跑步太无聊了，今晚九点操场集合，配速六分半左右，跑完一起去买烤肠，来的扣 1。",
             False, 20, 534, 23, 31),
            (2, "confession", "谢谢帮我捡书的同学",
             "今天在教学楼楼梯间书掉了一地，有个穿黑卫衣的同学帮我捡完就走了，都没来得及问名字。谢谢你，希望你能看到！",
             True, 30, 678, 56, 9),
            (1, "question", "食堂哪个窗口不辣",
             "广东人求问，二食堂有没有不辣的窗口？随便点个菜都是辣的，孩子想吃点清淡的。",
             False, 50, 743, 31, 27),
        ]
        posts = []
        for idx, slug, title, content, anon, h, views, likes, ccnt in posts_data:
            p = Post(user_id=users[idx].id, category_id=cats[slug].id, title=title, content=content,
                     is_anonymous=anon, view_count=views, like_count=likes, comment_count=ccnt,
                     created_at=ago(h), is_top=(slug == "confession" and h == 3))
            db.add(p)
            posts.append(p)
        await db.commit()
        for p in posts:
            await db.refresh(p)

        comments_data = [
            (0, 1, "白裙女生表示看到了（不是", 4),
            (0, 2, "勇敢一点！明天我帮你占旁边的位置", 3.5),
            (0, 3, "三食堂二楼+1，我也经常见到", 3),
            (1, 0, "我们老师更狠，还要随机点名回答问题", 4.5),
            (1, 3, "早八人的命也是命", 4),
            (2, 0, "三楼最里面靠窗倒数第二个，亲测有电", 7),
            (2, 4, "建议自带排插，一劳永逸", 6),
            (3, 4, "车还在吗？想要！", 9),
            (3, 0, "80 有点贵吧，50 收了", 8),
            (4, 0, "帮顶，昨天好像在操场门口看到过", 24),
            (5, 4, "1，九点准时到", 19),
            (5, 3, "1，烤肠我要两根", 18),
            (7, 2, "二楼潮汕窗口！牛肉丸汤粉不辣", 48),
            (7, 1, "同广东人，已经学会自己带饭了", 46),
        ]
        for pidx, uidx, text, h in comments_data:
            db.add(Comment(post_id=posts[pidx].id, user_id=users[uidx].id,
                           content=text, like_count=max(1, 20 - int(h)), created_at=ago(h)))
        await db.commit()

        # 一条待处理举报（举报二手帖）
        db.add(Report(reporter_id=users[1].id, target_type="post", target_id=posts[3].id,
                      target_user_id=posts[3].user_id, reason="spam",
                      detail="疑似广告引流，价格可疑",
                      target_snapshot=f"{posts[3].title}\n{posts[3].content}",
                      status="pending", created_at=ago(2)))
        # 一条已处理举报
        db.add(Report(reporter_id=users[0].id, target_type="comment", target_id=1,
                      target_user_id=users[1].id, reason="abuse", detail="言语不当",
                      target_snapshot="评论内容快照", status="rejected",
                      handler_id=1, handle_remark="未发现违规", created_at=ago(40),
                      handled_at=ago(38)))

        # 私信会话：demo1 <-> demo2
        u1, u2 = sorted([users[0].id, users[1].id])
        conv = Conversation(user1_id=u1, user2_id=u2, last_content="明天三食堂见！",
                            last_sender_id=users[0].id, last_message_at=ago(2))
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        db.add_all([
            Message(conversation_id=conv.id, sender_id=users[1].id,
                    content="在吗？你昨天说的那个女生，我好像认识", created_at=ago(3), is_read=True),
            Message(conversation_id=conv.id, sender_id=users[0].id,
                    content="真的吗！快告诉我", created_at=ago(2.5), is_read=True),
            Message(conversation_id=conv.id, sender_id=users[0].id,
                    content="明天三食堂见！", created_at=ago(2), is_read=False),
        ])
        await db.commit()

    print("演示数据生成完成")
    print("  手机端演示账号：demo1 / demo123456")
    print("  管理后台：admin / admin123456")


if __name__ == "__main__":
    asyncio.run(main())
