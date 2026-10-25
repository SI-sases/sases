p = 'core/services/swarm/prompts.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

print("=== 检查核心规则是否存在 ===")
print("1. 【前端修改与自我证伪铁律】:", "存在" if "【前端修改与自我证伪铁律" in c else "不存在")
print("2. 【深度排障与不放弃原则】:", "存在" if "【深度排障与不放弃原则" in c else "不存在")
print("3. 【第一铁律：严禁凭空修改】:", "存在" if "【第一铁律：严禁凭空修改】" in c else "不存在")
print("4. 【执行铁律（最高优先级，严禁违背）】:", "存在" if "【执行铁律（最高优先级，严禁违背）】" in c else "不存在")

print("\n=== 当前 Prompt 篇幅 ===")
print(f"文件总行数: {len(c.splitlines())}")
print(f"文件总字符数: {len(c)}")
