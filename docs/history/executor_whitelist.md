# 执行员命令白名单

## 一、白名单命令（17 条）

dir / ls / tree / type / cat / head / tail / findstr / find / grep / where / echo / pwd / cd / whoami / hostname / wc

## 二、危险字符黑名单（10 个）

& < > ^ % ; ` $ 换行符

管道符 | 允许，但会拆分逐段检查。

## 三、执行限制

- 超时：30 秒/命令
- 输出上限：2000 字符
- 编码：UTF-8 smart_decode（依次尝试 utf-8 / gbk / latin-1）

## 四、身份说明

SASES 里有三个角色：
- 指挥官（Commander）：拆解任务，不执行命令
- 执行员（Executor）：执行白名单命令，受上面 17 条限制
- 审核员（Reviewer）：判定每步 pass 或 retry，不执行命令

只有执行员有命令白名单。指挥官和审核员不执行 shell 命令。

## 五、常见问题

问：三者的白名单有哪些？
答：只有执行员有白名单，17 条命令见第一节。指挥官和审核员不执行 shell 命令，没有白名单。
