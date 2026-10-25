import os

me_js = 'static/modules/me.js'
if not os.path.exists(me_js):
    print("❌ 找不到 me.js 文件")
    exit()

with open(me_js, 'r', encoding='utf-8') as f:
    code = f.read()

inject_code = """
// ====== 强制接管设置页面交互 ======
document.addEventListener('DOMContentLoaded', () => {
    const bind = (id, fn) => {
        const el = document.getElementById(id);
        if (el) el.onclick = fn;
    };

    // 1. 账号与安全
    bind('set-account', () => {
        const sasesId = localStorage.getItem('sases_id') || '未知';
        alert(`【账号与安全】\\n当前 SASES ID: ${sasesId}\\n您的数据默认存储于本地，请妥善保管您的设备安全。`);
    });

    // 2. 授粉计划
    bind('set-pollination', () => {
        alert('【授粉计划】\\n当您的 AI 智能体生成的优秀解决方案被其他人复用时，您将获得被动积分奖励。\\n当前状态：已开启。');
    });

    // 3. 记忆管理
    bind('set-memory', () => {
        if (typeof openMemoryPage === 'function') {
            openMemoryPage();
        } else {
            alert('【记忆管理】\\n该功能正在开发中，敬请期待。');
        }
    });

    // 4. 通知设置
    bind('set-notify', () => {
        alert('【通知设置】\\n系统通知已在浏览器层级开启。\\n如需关闭，请在浏览器设置中禁止本站弹出通知。');
    });

    // 5. 隐私政策（直接打开网页）
    bind('set-privacy', () => {
        window.open('/static/privacy.html', '_blank');
    });

    // 6. 用户协议
    bind('set-agreement', () => {
        window.open('/static/agreement.html', '_blank');
    });

    // 7. 语言设置
    bind('set-language', () => {
        alert('【语言设置】\\n目前系统界面已完美适配中文。\\n英文翻译功能即将在后续版本更新中提供。');
    });

    // 8. 关于 SASES（展示开源信息）
    bind('set-about', () => {
        alert('【关于 SASES】\\n版本：v1.0.0-Release\\n\\n本项目基于 MIT 协议开源。\\nGitHub: https://github.com/SI-sases/sases\\n\\n个人使用免费，商业化需获得官方授权。');
    });
});
// ===================================
"""

# 如果之前没有注入过，就追加到文件末尾
if "强制接管设置页面交互" not in code:
    with open(me_js, 'a', encoding='utf-8') as f:
        f.write("\n" + inject_code)
    print("✅ 设置页面交互代码已成功注入 me.js")
else:
    print("☑️ 设置页面交互已存在，跳过注入")
