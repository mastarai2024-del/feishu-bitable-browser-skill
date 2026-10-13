# 飞书多维表格网页登录 Skill

让 Codex 等 Agent 用你自己的飞书网页登录操作多维表格。适合无法让管理员专门添加机器人的用户，包含新电脑安装、登录、建表整理与写后核验流程。

**无需飞书 App ID、Secret 或新建机器人；需要账号本来就有目标资源权限。** 扫码、验证码、MFA和组织选择仍由使用者完成。

## 最快开始

把这段发给你的 Agent：

```text
请从 https://github.com/mastarai2024-del/feishu-bitable-browser-skill 安装 feishu-bitable-browser Skill。
按 README 和 references/setup.md 选择当前系统支持的浏览器路线，完成环境检查。
登录步骤交给我本人处理；登录后先读取我提供的真实飞书表格。
保存修改前数据，核对改动范围，执行我明确要求的操作。批量改动先试写一条并刷新确认，最后逐条回读。
没有授权的删除、权限修改、公开分享、通知或付费操作不要执行。
```

手动安装，在仓库根目录运行：

没有Git也可以[下载ZIP](https://github.com/mastarai2024-del/feishu-bitable-browser-skill/archive/refs/heads/main.zip)，解压后在该文件夹打开终端，直接运行`python install_skill.py`。

```bash
git clone https://github.com/mastarai2024-del/feishu-bitable-browser-skill.git
cd feishu-bitable-browser-skill
python install_skill.py
```

macOS/Linux可用`python3`，Windows可用`py -3`。默认安装到当前用户的`~/.agents/skills/feishu-bitable-browser`。调用`$feishu-bitable-browser`；没显示时重启Agent。

## 新电脑选路线

| 环境 | 路线 |
| --- | --- |
| macOS，已安装EGO Lite | 使用ego-browser Skill与该浏览器登录态 |
| Windows/macOS/支持的Linux，Python 3.11+ | 本仓库独立Playwright Chromium |
| Agent已有可用浏览器工具 | 使用该工具实际控制的浏览器 |

EGO Lite目前公开支持macOS；Playwright具体系统要求以[官方文档](https://playwright.dev/python/docs/intro)为准。跨平台流程已提供，不代表每种新电脑和每个公司账号均实测通过。

通用路线在仓库根目录运行：

```bash
python skills/feishu-bitable-browser/scripts/bootstrap.py
python skills/feishu-bitable-browser/scripts/run.py doctor
python skills/feishu-bitable-browser/scripts/run.py login --url "你有权限的真实飞书资源链接"
```

`doctor`只检查本地Chromium。之后在弹出的浏览器里扫码。Profile保存在本机用户目录，不传给别人，也不放进Git。安装、权限与排错详见[新电脑流程](skills/feishu-bitable-browser/references/setup.md)。

## 能力与边界

Agent可按用户要求在正常网页创建Base、数据表、字段、视图和记录，并回读验收。可执行helper聚焦**源电子表格分组 → 现有单选字段分类更新**，不是完整飞书API替代。

分类helper会保留原选项、生成唯一匹配计划、保存旧值、检查并发、试写一条、刷新确认、字段级更新并逐条核对。歧义与保存状态不明时停止；数据量超过5000条时需另行定义范围。

```bash
python skills/feishu-bitable-browser/scripts/run.py read --url "目标链接，包含真实table参数" --output "私有任务目录/before.json"
python skills/feishu-bitable-browser/scripts/run.py export-sheet --url "源电子表格链接" --output "私有任务目录/source.xlsx"
python skills/feishu-bitable-browser/scripts/run.py map --source-xlsx "私有任务目录/source.xlsx" --sheet "实际工作表名" --snapshot "私有任务目录/before.json" --output "私有任务目录/plan.json" --group-column B --title-column C --description-column D
python skills/feishu-bitable-browser/scripts/run.py apply --plan "私有任务目录/plan.json"
```

最后一条是dry run，不能写入。审查计划且用户已授权这些具体改动后加`--commit`。模块单元格含备注时可以明确使用`--group-label first-line`，默认保留整个单元格。[完整对应流程](skills/feishu-bitable-browser/references/mapping.md)。

网页内部模型可能随版本变化，适配器不兼容时会停止；其它编辑走正常UI。[适配器与证据边界](skills/feishu-bitable-browser/references/adapter.md)。

## 更新、恢复与验证

同名Skill默认不覆盖。已授权更新时用`python install_skill.py --replace`，旧副本先备份。失败时查看私有运行目录的journal与旧值，先核对已提交结果，避免重复跑未知状态的写入。

在源仓库运行以下命令，它会自动使用已安装的runtime Python：

```bash
python skills/feishu-bitable-browser/scripts/run.py test
```

测试只操作合成数据与本机页面，不访问真实飞书或付费API。当前结果与未验证项见[VALIDATION.md](VALIDATION.md)。实际任务数据、账号profile和公司链接不收入仓库。

English: an original, bot-free Feishu Bitable agent skill. Install with `python install_skill.py`, bootstrap the private Chromium runtime, log in with your own authorized account, and ask the agent to follow `SKILL.md`. Executable helpers automate single-select classification updates only; other tasks use the normal UI. This skill does not grant access or transfer another person's session.

## 来源与许可

独立编写的操作流程和代码，没有复制豆包专有Skill或公司数据。MIT License；不隶属于飞书、豆包、EGO或OpenAI。

- [Codex技能位置与发现](https://learn.chatgpt.com/docs/build-skills)
- [EGO Lite官方仓库](https://github.com/citrolabs/ego-lite)
- [Playwright安装与系统要求](https://playwright.dev/python/docs/intro)
- [浏览器安装](https://playwright.dev/python/docs/browsers)
