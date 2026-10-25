REQUIRE_TASK_CONFIRMATION = False

# 草稿模式前缀（全角冒号和半角冒号都可以）
COMMAND_PREFIX_MAP = {
    # (#0 由 send_message 早分支拦截，无需在 MAP 中登记)
    "#0:": "unlock",
    "#0：": "unlock",
    "#1:": "exec", "#1：": "exec",
    "#2:": "task", "#2：": "task",
    "#3:": "draft", "#3：": "draft",
    "#4:": "auto", "#4：": "auto",
}

DRAFT_PREFIXES = ("草稿：", "草稿:", "编辑：", "编辑:")
