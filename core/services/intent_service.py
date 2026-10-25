# core/services/intent_service.py
"""
意图识别：判断用户输入是"普通聊天"还是"可执行任务"

两层判断：
1. 规则过滤（零成本）：快速命中闲聊或任务
2. LLM 判断（仅中间地带）：调一次轻量 LLM
"""
import asyncio
import re
import openai

from .. import config

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=60,
    max_retries=1
)

MODEL = config.MODEL_NAME

# ========== 第一层：规则 ==========

# 纯聊天（命中即判定为 chat，不再调 LLM）
CHAT_PATTERNS = [
    r'^(你好|您好|hi|hello|hey|嗨|哈喽)[\s!！。.？?]*$',
    r'^(谢谢|感谢|thanks|thank you)[\s!！。.]*$',
    r'^(好的|是的|对|嗯|ok|okay|明白|收到|知道了)[\s!！。.]*$',
    r'^(再见|拜拜|晚安|早安|bye)[\s!！。.]*$',
    r'^[\s\?？!！。.…]+$',           # 纯标点
    r'^[\U0001F300-\U0001F9FF\s]+$',  # 纯 emoji
]

# 任务关键词（动词）
TASK_VERBS = [
    "列出", "查看", "打开", "执行", "运行", "启动", "创建", "删除", "查找", "搜索",
    "复制", "移动", "重命名", "安装", "卸载", "下载", "上传", "压缩", "解压",
    "统计", "分析", "计算", "检查", "测试", "编译", "构建", "部署",
    "看", "读", "写", "改", "跑", "查", "找", "拿",
    "有多少", "多少个", "几个", "计数", "数一数", "比较", "对比",
    "抓取", "获取", "爬取", "拉取", "请求", "访问",
]

# 任务关键词（名词）
TASK_NOUNS = [
    "目录", "文件", "文件夹", "进程", "端口", "服务", "系统", "盘", "路径",
    "环境", "配置", "日志", "代码", "脚本", "命令", "项目", "仓库",
    "函数", "变量", "类", "方法", "模块", "行", "函数名", "变量名",
    "Python", "JS", "JavaScript", "Java", "Go", "Rust",
    "网页", "链接", "网址", "内容", "页面", "站点", "网站",
    "字符", "文字", "字数", "字符串", "工具", "中文", "数据", "结果",
    "报告", "表格", "列表", "文档", "图表", "摘要", "要点",
]

# 路径特征：C:\、D:\、/usr/、./、../、*.ext
PATH_PATTERN = re.compile(r'([A-Za-z]:\\|/[a-z]+/|\.\/|\.\.\/|\*\.[a-z]+)')

# URL 特征
URL_PATTERN = re.compile(r'https?://[^\s]+', re.IGNORECASE)

# 文件扩展名特征
FILE_EXT_PATTERN = re.compile(
    r'\.(js|py|md|json|txt|html|css|log|db|yaml|yml|toml|bat|sh|exe|zip|csv|xml|ini|cfg|conf|sql)\b',
    re.IGNORECASE
)


def _is_obvious_chat(content: str) -> bool:
    text = content.strip()
    if not text:
        return True
    if len(text) < 4:
        return True
    for pattern in CHAT_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    return False


def _is_obvious_task(content: str) -> bool:
    text = content.strip()
    # 路径特征
    if PATH_PATTERN.search(text):
        return True
    # URL 特征
    if URL_PATTERN.search(text):
        return True
    # 文件扩展名特征
    if FILE_EXT_PATTERN.search(text):
        return True
    # 操作动词（单字，覆盖更广）
    if re.search(r'(搜|查|找|看|读|写|改|跑|列|删|加|建|拿|抓|拉|发|传|算|数|比|统计|分析|整理|翻|捞|整|搞|弄)', text):
        return True
    # 动词 + 名词组合
    for verb in TASK_VERBS:
        if verb in text:
            for noun in TASK_NOUNS:
                if noun in text:
                    return True
    return False


async def _llm_judge(content: str) -> bool:
    """调 LLM 判断是否为任务，返回 True 表示是任务"""
    prompt = f"""判断用户输入属于以下哪一类，只回答一个字母：

A) 纯聊天（问候、寒暄、情感表达，不需要任何工具）
   例：你好、谢谢、今天心情不错、随便聊聊

B) 需要执行的任务（需要读文件/搜代码/执行命令/访问网络/调用工具）
   例：搜一下 X、读 Y 文件、看看 Z 目录、抓取这个网页、统计某字数

判断规则：
- 输入含"搜、查、找、读、改、跑、列、看、抓、下载、统计、分析"等操作词 → B
- 需要访问文件系统/网络/数据库才能回答 → B
- 只有纯粹的情感交流或闲聊 → A

用户输入：{content}

只回答 A 或 B。"""

    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5
        )
        answer = resp.choices[0].message.content.strip().upper()
        return answer.startswith("B")
    except Exception:
        # LLM 不可用时，默认走普通聊天，避免误触发
        return False


async def is_task_intent(content: str) -> bool:
    """
    判断用户输入是否为可执行任务
    """
    if not content or not content.strip():
        return False

    # 上下文疑问句：优先判为对话（避免"刚才你改了什么"被误判为任务）
    _ctx_q_prefixes = ('刚才', '你刚才', '刚刚', '上次', '之前', '你之前', '前面你', '前面那', '刚刚那')
    _ctx_q_kws = ('哪一行', '哪个文件', '哪一处', '哪一个', '是什么', '是什么样', '还记得', '记得吗', '在哪', '哪几行', '哪个位置')
    _text_stripped = content.strip()
    if any(_text_stripped.startswith(p) for p in _ctx_q_prefixes):
        if any(kw in _text_stripped for kw in _ctx_q_kws):
            return False

    # 第一层：规则
    if _is_obvious_chat(content):
        return False

    if _is_obvious_task(content):
        return True

    # 第二层：LLM 判断（中间地带）
    llm_result = await _llm_judge(content)
    if not llm_result:
        # 兜底：LLM 判 chat，但内容含操作动词 → 仍判 task
        if re.search(r'(搜|查|找|看|读|写|改|跑|列|抓|下载|统计|分析)', content):
            return True
    return llm_result
