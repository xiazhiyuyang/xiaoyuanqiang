"""规则层：正则模式识别。

词库（DFA）擅长「已知词」，规则层擅长「有结构的信息」：
联系方式、网址、二维码引导、兼职刷单话术、代写代考、赌博、涉枪涉爆、
隐私泄露（手机号/身份证号）、学术不端、轻生倾向等。

每条规则带 category / severity / action / weight，
最终由 decision.py 结合词库命中与特征分统一裁决。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .normalize import compact, deep_normalize


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    category: str          # 违规分类，取值见 categories.py
    severity: int          # 1-5
    action: str            # block / review / mask
    weight: int            # 命中后贡献的风险分
    pattern: str
    note: str = ""
    flags: int = re.IGNORECASE


@dataclass
class RuleHit:
    rule_id: str
    name: str
    category: str
    severity: int
    action: str
    weight: int
    matched: str
    note: str = ""


# 规则表
RULES: tuple[Rule, ...] = (
    Rule(
        "contact_wechat", "微信引流", "ad", 4, "review", 35,
        r"(?:加|留|私|戳|扫|\+)?\s*(?:微信|薇信|嶶信|溦信|威信|v信|w信|微❤?信|vx|wx|v\s*x|weixin|wechat|v\s*:\s*|扣扣)\s*(?:号|号码)?\s*[:：]?\s*[a-z0-9_\-]{4,20}",
        "疑似导流到站外微信/QQ，需人工确认是否为正常交流",
    ),
    Rule(
        "contact_wechat_bare", "微信关键词", "ad", 3, "review", 22,
        r"(?:加|留|私)\s*(?:微信|薇信|威信|v信|vx|wx|微❤?信)",
        "出现诱导加微信话术",
    ),
    Rule(
        "contact_qq", "QQ 号引流", "ad", 3, "review", 22,
        r"(?:qq|扣扣|企鹅)\s*(?:号)?\s*[:：]?\s*\d{5,12}",
    ),
    Rule(
        "contact_telegram", "Telegram 引流", "ad", 4, "review", 30,
        r"(?:telegram|电报|飞机|tg)\s*(?:号|群)?\s*[:：]?\s*@?\s*[a-z0-9_]{4,32}",
        "站外匿名即时通讯引流，诈骗高发渠道",
    ),
    Rule(
        "contact_phone", "手机号泄露", "privacy", 3, "mask", 26,
        r"(?<!\d)1[3-9]\d{9}(?!\d)",
        "手机号已打码，建议改用站内私信联系",
    ),
    Rule(
        "contact_idcard", "身份证号", "privacy", 5, "block", 70,
        r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)",
        "严禁发布他人身份证号码",
    ),
    Rule(
        "contact_bankcard", "银行卡号", "privacy", 5, "block", 60,
        r"(?<!\d)\d{16,19}(?!\d)",
        "疑似银行卡号，存在盗刷与洗钱风险",
    ),
    Rule(
        "qrcode_guide", "二维码引导", "ad", 3, "review", 24,
        r"(?:扫码|扫一扫|长按识别|识别二维码|扫下方|扫上面)",
        "引导扫码，需人工确认二维码内容",
    ),
    Rule(
        "url_external", "外链推广", "ad", 3, "review", 22,
        r"(?:https?://|www\.)[a-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]{4,120}",
        "正文含外链，需人工确认是否为推广或钓鱼",
    ),

    Rule(
        "fraud_parttime", "兼职刷单", "fraud", 5, "block", 70,
        r"(?:兼职|刷单|刷信誉|垫付|日结|日入|躺赚|轻松赚|无门槛|返利|做任务).{0,14}(?:佣金|提成|日结|结算|返现|赚|收入|加我|联系|私聊)",
        "典型刷单返利诈骗话术",
    ),
    Rule(
        "fraud_loan", "校园贷 / 套现", "fraud", 5, "block", 65,
        r"(?:无抵押|秒下款|低息|网贷|现金贷|花呗套现|信用卡套现|校园贷|裸贷|助学金贷|分期套现)",
        "非法借贷与套现",
    ),
    Rule(
        "fraud_money_launder", "跑分洗钱", "fraud", 5, "block", 75,
        r"(?:跑分|洗钱|代收款|出租银行卡|出租电话卡|四件套|收卡|买卖账户|代收付)",
        "涉洗钱黑灰产",
    ),
    Rule(
        "gambling", "网络赌博", "fraud", 5, "block", 70,
        r"(?:博彩|赌场|赌博网|六合彩|时时彩|北京赛车|棋牌|下注|投注|倍投|返水|娱乐城|威尼斯人|澳门赌|网投)",
        "涉赌内容",
    ),
    Rule(
        "drugs", "涉毒", "illegal", 5, "block", 85,
        r"(?:冰毒|摇头丸|麻古|氯胺酮|k粉|笑气|上头电子烟|大麻|可卡因|海洛因|吸毒|贩毒)",
        "涉毒违法信息",
    ),
    Rule(
        "weapon", "涉枪涉爆", "illegal", 5, "block", 85,
        r"(?:出售|买|卖|求|收).{0,6}(?:枪支|手枪|步枪|子弹|雷管|炸药|管制刀具|砍刀|甩棍|弩|催泪器)",
        "涉枪涉爆违法交易",
    ),
    Rule(
        "fake_document", "假证假章", "illegal", 5, "block", 70,
        r"(?:办证|办假证|假毕业证|假学历|刻章|代开发票|虚开发票|假身份证)",
        "伪造证件票据",
    ),

    Rule(
        "academic_ghost", "代写代考", "academic", 5, "block", 65,
        r"(?:代写|代做|代考|替考|枪手|包过|保过|论文降重|降重服务|代写论文|代写作业|代做课设|代做毕设)",
        "学术不端行为，校园墙明令禁止",
    ),
    Rule(
        "academic_answer", "出售答案", "academic", 5, "block", 65,
        r"(?:出售|提供|有|求).{0,6}(?:考试答案|试卷答案|四六级答案|答案|原题)",
        "涉嫌考试作弊",
    ),
    Rule(
        "academic_substitute", "代课代签", "academic", 4, "review", 40,
        r"(?:代课|代签|代体测|代跑|代刷课|刷网课|代打卡|替课|代升旗|代值日)",
        "校园代课代签等违规服务",
    ),

    Rule(
        "porn_service", "色情服务", "porn", 5, "block", 80,
        r"(?:约炮|一夜情|上门服务|特殊服务|援交|包养|福利姬|裸聊|原味|福利视频|全套服务|外围|上门按摩)",
        "涉黄违法信息",
    ),
    Rule(
        "porn_minor", "涉未成年人", "minor", 5, "block", 95,
        r"(?:未成年|初中生|小学生|萝莉|幼女|正太).{0,8}(?:裸|色|视频|照片|资源|福利)",
        "涉未成年人不良信息，零容忍",
    ),

    Rule(
        "abuse_curse", "恶毒辱骂", "abuse", 3, "mask", 30,
        r"(?:死全家|全家死|去死吧|你个废物|滚出学校|祝你死|死妈|nmsl|你妈死)",
        "人身攻击，已打码",
    ),
    Rule(
        "doxx", "人肉开盒", "privacy", 5, "block", 80,
        r"(?:人肉|开盒|查户籍|扒出|曝光).{0,10}(?:姓名|手机号|身份证|学号|宿舍|家庭住址|照片|父母)",
        "人肉搜索与隐私侵害",
    ),
    Rule(
        "threat", "威胁恐吓", "violence", 4, "review", 45,
        r"(?:弄死你|打死你|砍你|找人打|堵你|报复你|见一次打一次)",
        "涉及人身威胁",
    ),

    Rule(
        "self_harm", "轻生倾向", "self_harm", 4, "review", 45,
        r"(?:自杀|轻生|割腕|跳楼|跳河|安眠药|烧炭|不想活|活不下去|结束生命)",
        "疑似轻生倾向，需人工关怀介入（请勿直接删除）",
    ),

    Rule(
        "spam_ad_soft", "软性推广", "ad", 2, "review", 14,
        r"(?:招代理|诚招代理|一件代发|微商|加盟|带货|全网最低|低价出|清仓|引流|涨粉|刷粉|刷赞)",
        "疑似营销推广",
    ),
    Rule(
        "spam_repeat", "重复刷屏", "spam", 2, "mask", 12,
        r"(.{2,8})\1{4,}",
        "短时间内大量重复内容",
    ),
)

_COMPILED: tuple[tuple[Rule, re.Pattern], ...] = tuple(
    (r, re.compile(r.pattern, r.flags)) for r in RULES
)

# 校园墙正常语境白名单：命中这些词不单独构成违规（降低误伤）
ALLOW_HINTS = (
    "二手", "出售", "求购", "失物招领", "捡到", "丢了", "寻物",
    "社团", "招新", "志愿者", "活动报名", "讲座", "比赛",
)


def scan_rules(text: str, *, rules: tuple[tuple[Rule, re.Pattern], ...] = _COMPILED) -> list[RuleHit]:
    """在「原文 / 紧凑形式 / 深度归一」三个视角上跑规则。

    - 原文：保留标点语义（如 URL、金额）；
    - 紧凑形式：识破「加 微 信」式跳字绕过；
    - 深度归一：识破谐音（薇信）、重复字符灌水等变形。
    """
    if not text:
        return []
    hits: list[RuleHit] = []
    seen: set[str] = set()
    views = [text]
    for transform in (compact, deep_normalize):
        try:
            view = transform(text)
        except Exception:
            continue
        if view and view not in views:
            views.append(view)
    for view in views:
        for rule, pattern in rules:
            for m in pattern.finditer(view):
                key = f"{rule.id}:{m.group(0)[:32]}"
                if key in seen:
                    continue
                seen.add(key)
                hits.append(RuleHit(
                    rule_id=rule.id, name=rule.name, category=rule.category,
                    severity=rule.severity, action=rule.action,
                    weight=rule.weight, matched=m.group(0)[:60], note=rule.note,
                ))
    return hits


def rule_catalog() -> list[dict]:
    """供后台展示当前生效的规则。"""
    return [
        {
            "id": r.id, "name": r.name, "category": r.category,
            "severity": r.severity, "action": r.action, "weight": r.weight,
            "note": r.note, "pattern": r.pattern,
        }
        for r in RULES
    ]
