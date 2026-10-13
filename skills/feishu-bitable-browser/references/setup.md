# 新电脑安装与登录

需要支持的桌面系统、Python 3.11+、可下载Python包及浏览器的网络，以及有目标权限的飞书账号。公司资源的访问、编辑和下载限制继续有效。

宿主Agent需要能读取本地Skill并运行本地命令或控制浏览器，例如Codex或Claude Code。没有Git时用仓库的Download ZIP解压；Git只是克隆源码的一种方式，不是运行Skill的必需依赖。

## 安装Skill

仓库根目录运行`python install_skill.py`；macOS/Linux可用`python3`，Windows可用`py -3`。默认路径为`~/.agents/skills/feishu-bitable-browser`，符合[Codex官方用户技能位置](https://learn.chatgpt.com/docs/build-skills)。其它宿主显式传实际目录，如`--destination ~/.claude/skills`。调用`$feishu-bitable-browser`，不显示时重启Agent。

同名目录默认停止；明确更新时`--replace`会先备份到私有runtime的`skill-backups/`，不改全局Agent配置或无关Skill。

## EGO Lite（macOS）

从[官网](https://lite.ego.app/)安装应用并完成onboarding，按[官方安装参考](https://github.com/citrolabs/ego-lite/blob/main/skills/ego-browser/references/install.md)操作。只安装ego-browser Skill不代表浏览器已安装。

检查：`ego-browser nodejs -e "console.log('runtime-ready')"`。

Agent创建专用TaskSpace并打开实际资源。跳转登录页时交还用户；用户确认后接管同一个空间。已有带标签的`p1`用`task.page('p1')`；只有`task.tabs()`中没有标签的Page才传给`task.adopt()`。不要用Page对象的`===`判断是否托管。

读取实际标题、字段和记录后才算资源读取通过。不要复制别人的profile、绝对目录、cookie或token。

## 独立Playwright（跨平台流程）

截至2026-10-13，EGO Lite官方公开支持macOS；通用路线使用Playwright支持的系统，详见[系统要求](https://playwright.dev/python/docs/intro)。Python缺失时从[python.org](https://www.python.org/downloads/)安装3.11+。

当前官方桌面系统列表包含Windows 11+/Windows Server 2019+、macOS 14+，以及Debian 12/13、Ubuntu 22.04/24.04/26.04（x86-64或arm64）。其它系统不承诺本helper可直接运行；先选择已有可用浏览器工具或核对官方支持范围。

```bash
python skills/feishu-bitable-browser/scripts/bootstrap.py
python skills/feishu-bitable-browser/scripts/run.py doctor
python skills/feishu-bitable-browser/scripts/run.py login --url "实际飞书链接"
```

安装器创建独立venv，安装固定依赖与Chromium，不改系统Python。Linux缺系统库时按[官方浏览器文档](https://playwright.dev/python/docs/browsers)处理；需要操作系统权限时说明具体依赖，不擅自修改系统。

Doctor只打开本地测试页，`feishu_access_verified: false`是正常的。Login弹出Skill自己的Chromium，由用户扫码、验证和选择组织，默认等待300秒；Agent后台运行并及时说明窗口位置。登录命令确认资源runtime加载后仍需`read`验证目标表及完整数据。

Runtime默认在用户目录`.cache/feishu-bitable-browser/`，包含`venv/`、`browser-profile/`和`runs/`。可用进程环境`FEISHU_SKILL_RUNTIME`改到另一个私有目录；不放在共享/Git目录。Profile不导出，不读取钥匙串，不复制其它浏览器登录态。

## 排错

| 现象 | 处理 |
| --- | --- |
| 浏览器可用但CLI返回131006 | 核对CLI账号/组织/资源ACL；可使用现有网页权限，不静默切bot |
| 新窗口要求登录 | 在该窗口登录，飞书桌面、EGO、内置浏览器与Skill Chromium登录态独立 |
| 已登录仍无权限 | 使用用户明确选择的有权限账号，或由所有者授权；Skill不绕过ACL |
| 不能下载源表 | 明确阻塞，按允许范围读取UI；不能冒充完整导出 |
| Profile占用 | 等本Skill上一进程结束，不结束用户其它浏览器或删除profile |
| ADAPTER_UNAVAILABLE/数据不完整 | 正常UI选择正确表及范围，结构变化时走UI或定向适配 |
| 截图超时 | 检查现状，仍失败时用刷新后的值回读并保留失败说明，不循环截屏 |

分别记录安装、读取、真实写入回读；不合并宣称所有电脑全部通过。
