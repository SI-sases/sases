# 用户自然语言任务模板

> 不需要记「执行：」。直接说人话即可。

## 改文件

```text
帮我把 static/modules/i18n.js 里的默认语言改成英文
把首页标题改成 “SASES 助手”
修复 static/modules/main.js 里语言按钮点击没反应的问题
在 static/index.html 的输入框下面加一个提示文字
```

## 新建 / 删除

```text
帮我新建一个 static/modules/help.js，里面放一个 showHelp 函数
删除 data/old.txt
把 data/a.txt 重命名成 data/b.txt
```

## 读取 / 查看

```text
读取 SASES.md 第一行
看一下 static/modules/i18n.js 现在默认语言是什么
统计 data/log.txt 有多少行 ERROR
在项目里找一下 verify_syntax 在哪定义
```

## 多步骤

```text
先读 i18n.js 和 main.js，再把默认语言改成英文，最后验证语法
读取 a.txt b.txt c.txt，汇总行数，写到 summary.txt，再读回来确认
```

## 带验证

```text
帮我改 main.js 的语言按钮，改完自己 verify_syntax，失败就修
改完前端后自己截图确认，不要让我检查
```

## 什么时候会进入执行

系统会自动识别这些动作：

```text
改 / 修复 / 创建 / 写入 / 删除 / 重命名 / 重构 / 实现 / 部署
读取 / 查看 / 统计 / 汇总 / 分析 / 检查 / 测试
```

如果识别不到，才需要显式写：

```text
执行：你的任务
```

## 写操作审批

默认分级：

```text
data/ static/ docs/ tests/        直接写
core/ scripts/ launcher/          需要审批
删除 / 重命名 / git / ssh / 部署  需要审批
run_python 含删除、rm、DROP       需要审批
仓库外路径 / .env / secrets        需要审批
```

用户会看到审批卡片，点允许后继续执行。

## 不建议的说法

```text
“你懂的”
“搞一下”
“弄好它”
```

尽量带上：

```text
文件 / 目录 / 目标 / 验收方式
```
