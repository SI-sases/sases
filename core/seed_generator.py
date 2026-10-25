import os
import json
import random
import re
import time
import openai

from core import config
from core import similarity

# ========== 领域关键词库 ==========
DOMAIN_KEYWORDS = {
    "算法与数据结构": ["排序", "搜索", "图", "树", "动态规划", "递归", "链表", "栈", "队列", "哈希", "堆", "并查集", "回溯", "贪心", "最短路径", "最小生成树"],
    "数据处理与分析": ["JSON", "CSV", "清洗", "解析", "转换", "过滤", "聚合", "统计", "数据帧", "pandas", "numpy", "缺失值", "异常值"],
    "人工智能/机器学习": ["分类", "预测", "回归", "聚类", "神经网络", "推荐", "特征工程", "梯度下降", "过拟合", "卷积", "循环神经网络", "自然语言处理"],
    "网络安全/代码审查": ["注入", "验证", "SQL", "XSS", "加密", "防火墙", "权限", "身份认证", "令牌", "安全扫描", "漏洞"],
    "系统设计与工具": ["缓存", "日志", "配置", "调度", "监控", "文件系统", "消息队列", "负载均衡", "API设计", "微服务"],
    "自动化脚本": ["批量", "重命名", "定时", "文件操作", "备份", "同步", "邮件", "爬虫", "网页抓取"],
    "自然语言处理": ["分词", "关键词", "摘要", "情感", "文本相似", "TF-IDF", "词向量", "命名实体", "机器翻译", "问答系统"],
    "金融": ["利率", "贷款", "股票", "保险", "汇率", "投资", "复利", "风险", "资产定价", "回测"],
    "医疗健康": ["诊断", "药物", "BMI", "剂量", "疫苗", "病历", "症状", "影像", "基因", "健康监测"],
    "教育学习": ["成绩", "考试", "题库", "GPA", "课程表", "排名", "学习路径", "知识图谱", "在线课程"],
    "艺术设计": ["色彩", "排版", "画布", "滤镜", "音乐", "和弦", "绘画", "设计模式", "图像处理"],
    "游戏开发": ["碰撞检测", "AI", "寻路", "技能冷却", "积分板", "排行榜", "关卡生成", "物理引擎"],
    "日常工具": ["计算器", "倒计时", "闹钟", "单位换算", "邮政编码", "日历", "天气", "汇率换算"],
    "办公效率": ["邮件合并", "表格处理", "PPT生成", "文档格式", "会议安排", "提醒", "待办事项"],
    "物流运输": ["路径规划", "装箱", "调度", "运费", "仓储", "供应链", "配送"],
    "航空航天": ["轨道", "火箭", "卫星", "燃料", "太空", "导航", "飞行控制"],
    "农业": ["灌溉", "施肥", "病虫害", "产量预测", "温室", "土壤", "气象"],
    "能源": ["电力", "石油", "太阳能", "风能", "储能", "电网", "智能电表"],
    "法律": ["合同", "法条", "判例", "知识产权", "版权", "合规", "诉讼"],
    "通信": ["5G", "信号", "频谱", "路由", "协议", "网络", "调制解调"],
    "制造": ["加工", "装配", "质检", "模具", "数控", "3D打印", "工业机器人"],
    "环境科学": ["污染", "监测", "排放", "回收", "生态", "气候", "碳足迹"],
    "心理学": ["情绪", "行为", "问卷", "量表", "认知", "压力", "心理健康"],
    "生物信息学": ["DNA", "蛋白质", "基因序列", "序列比对", "进化树", "基因组"],
    "地理信息": ["地图", "坐标", "GIS", "距离", "导航", "空间查询"],
    "电子商务": ["商品推荐", "购物车", "优惠券", "库存", "订单", "支付"],
    "社交媒体": ["好友推荐", "信息流", "点赞", "评论", "话题", "用户画像"],
    "图像处理": ["滤波", "边缘检测", "图像分类", "目标检测", "OCR", "图像增强"],
    "音频处理": ["降噪", "语音识别", "音频分类", "节拍检测", "合成"],
}

# ========== 辅助函数 ==========
def load_all_existing_descriptions():
    descriptions = set()
    kb_file = config.KB_FILE
    if os.path.exists(kb_file):
        with open(kb_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for item in data:
                    descriptions.add(item.get("task", ""))
            except:
                pass
    for fname in [config.MAIN_SEED_FILE, config.SEED_POOL_FILE]:
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        seed = json.loads(line)
                        if "description" in seed:
                            descriptions.add(seed["description"])
                    except:
                        pass
    return list(descriptions)

def _random_domains(num=1):
    domains = list(DOMAIN_KEYWORDS.keys())
    if num > len(domains):
        num = len(domains)
    return random.sample(domains, num)

def _build_seed_prompt(existing_descs, domains):
    selected_keywords = []
    for domain in domains:
        selected_keywords.append(random.choice(DOMAIN_KEYWORDS[domain]))
    domain_str = "、".join(domains)
    keyword_str = "、".join(selected_keywords)

    task_type = random.choice([
        "函数实现",
        "算法设计",
        "数据处理脚本",
        "类设计",
        "API调用示例",
        "数据转换工具",
        "自动化脚本",
        "查询优化",
        "性能分析",
        "单元测试生成",
    ])

    example = {
        "description": "如何判断一个信用卡号是否有效（Luhn算法）？",
        "difficulty": "easy",
        "domain": ["金融", "算法"],
        "test_cases": [
            {"input": "4532015112830366", "expected_output": True},
            {"input": "6011514433546201", "expected_output": False}
        ]
    }

    prompt = f"""请生成一个与【{domain_str}】领域相关的可编程任务，任务类型为：{task_type}。
任务描述必须是**自然语言提问**，不能使用人称，不能出现“编写一个Python函数”等机械开头。
描述应像现实世界中一个人向同伴求助的编程问题，尽量包含关键词：{keyword_str}。

示例：
{json.dumps(example, ensure_ascii=False)}

要求：
- 任务背景可以涉及任何领域或生活场景。
- domain 是一个字符串数组，表示涉及的一个或多个领域。
- difficulty 是 easy/medium/hard 之一。
- test_cases 至少包含1个用例，input 和 expected_output 使用纯Python字面量。
- 只输出一个合法的JSON对象，不要包含任何额外文字、解释或代码块标记。
- JSON 中所有字符串必须使用双引号包裹，不得使用单引号。
- 确保 JSON 格式正确，可以被 Python 的 json.loads 直接解析。"""
    return prompt

def _call_api(prompt):
    client = openai.OpenAI(
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
        timeout=120,
        max_retries=3
    )
    try:
        resp = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
            max_tokens=1000,
            response_format={"type": "json_object"}   # 强制 JSON 输出
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # 如果 response_format 不支持，回退到普通调用
        print(f"  JSON mode 调用失败，回退普通调用: {e}")
        resp = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
            max_tokens=1000
        )
        return resp.choices[0].message.content.strip()

def _parse_seed_response(raw):
    """更稳健的 JSON 解析：处理 BOM、代码块、提取第一个完整 JSON 对象"""
    if not raw:
        return None
    # 去除 BOM
    raw = raw.lstrip('\ufeff').strip()
    # 移除代码块标记
    if raw.startswith("```"):
        raw = re.sub(r'^```[a-zA-Z]*\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
    # 尝试直接解析
    try:
        return json.loads(raw)
    except:
        pass
    # 提取第一个 { 到最后一个 } 之间的内容，并尝试修复尾逗号等问题
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        candidate = match.group()
        # 移除尾逗号（简单处理）
        candidate = re.sub(r',\s*}', '}', candidate)
        candidate = re.sub(r',\s*]', ']', candidate)
        try:
            return json.loads(candidate)
        except:
            # 尝试替换单引号为双引号（但小心字符串内的单引号）
            # 这里不做深入修复，返回 None
            return None
    return None

def generate_single_seed(existing_descs, max_attempts=8):
    for attempt in range(max_attempts):
        num_domains = random.randint(1, 3)
        domains = _random_domains(num_domains)
        prompt = _build_seed_prompt(existing_descs, domains)

        try:
            raw = _call_api(prompt)
            task = _parse_seed_response(raw)
        except Exception as e:
            print(f"  [尝试{attempt+1}] API调用失败: {e}")
            time.sleep(2)
            continue

        if not task:
            print(f"  [尝试{attempt+1}] JSON解析失败")
            continue

        desc = task.get("description")
        if not desc:
            print(f"  [尝试{attempt+1}] 缺少 description")
            continue

        test_cases = task.get("test_cases")
        if not test_cases or not isinstance(test_cases, list) or len(test_cases) < 1:
            print(f"  [尝试{attempt+1}] 缺少 test_cases 或为空")
            continue

        if desc.startswith("编写一个") or desc.startswith("请编写一个"):
            print(f"  [尝试{attempt+1}] 机械开头，丢弃")
            continue

        if existing_descs and similarity.is_similar(desc, existing_descs, threshold=config.SIMILARITY_THRESHOLD):
            print(f"  [尝试{attempt+1}] 语义相似，跳过")
            continue

        task["domain"] = _normalize_domains(task.get("domain"))
        print(f"  [成功] {desc[:50]}...")
        return task

    print("  多次尝试均失败，返回 None")
    return None

def generate_new_seeds(num=10):
    existing_descs = load_all_existing_descriptions()
    seeds = []
    for i in range(num):
        seed = generate_single_seed(existing_descs)
        if seed:
            seeds.append(seed)
            existing_descs.append(seed["description"])
            print(f"  [{len(seeds)}] {seed['description'][:70]}... (领域: {'+'.join(seed.get('domain', []))})")
        else:
            print(f"  第{i+1}个种子生成失败，等待后继续...")
            time.sleep(5)
        time.sleep(0.5)
    return seeds

def _normalize_domains(domain_field):
    if domain_field is None:
        return ["综合"]
    if isinstance(domain_field, list):
        return list(set(domain_field)) or ["综合"]
    if isinstance(domain_field, str):
        parts = re.split(r'[,;，；]\s*', domain_field)
        if len(parts) > 1:
            return list(set(parts))
        return [domain_field]
    return ["综合"]
