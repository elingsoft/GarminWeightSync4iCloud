# Repository Guidelines

## 项目结构与模块组织

- `scripts/` 是唯一现行实现：`watcher.py` 扫描并处理称重文件，`fit_weight.py` 生成 FIT，`login_once.py` 缓存 Garmin token，`com.user.weighin.plist` 是 launchd 模板。
- 仓库不包含 `weighin/` 目录；`scale-sync-mac.zip` 是被 `.gitignore` 排除的历史归档，不作为修改依据。
- `Logs/` 保存运行日志和去重账本（`weighin.log`、`weighin.err`、`uploaded.json`），不得提交。
- `venv/` 是本地虚拟环境，不得提交。
- `docs/` 保存专项文档：Mac 端部署与排错以 `docs/mac-setup.md` 为准，快捷指令说明见 `docs/shortcut-icloud.md`。
- `README.md` 是默认英文版，`README.zh-CN.md` 是中文版。任何 README 内容变更必须在同一次提交中同步更新两种语言，并互相保留语言切换链接。

## 构建、测试与开发命令

```bash
python3 -m venv venv
./venv/bin/pip install garminconnect curl_cffi
./venv/bin/python -m py_compile scripts/*.py
./venv/bin/python scripts/fit_weight.py
GARMIN_EMAIL="you@example.com" ./venv/bin/python scripts/login_once.py
./venv/bin/python scripts/watcher.py
plutil -lint scripts/com.user.weighin.plist
```

以上命令依次创建环境、安装依赖、检查语法、生成 `/tmp/test_weight.fit`、交互式登录、执行一次扫描并校验 launchd 模板。替换真实路径和邮箱占位符后，再使用 `launchctl`。

`watcher.py` 只在 `ACTIVE_WINDOWS`（默认 5:00–9:00、20:00–22:00）内处理文件；窗口外手动运行是正常的空操作。`login_once.py` 需要交互输入密码，不纳入自动化测试。

## 架构与数据流

iPhone 快捷指令把 JSON 写入 iCloud Drive 的 `WeightIn`；`watcher.py` 按日期和体重去重，生成 FIT 并上传，只有确认成功后才删除源文件。修改时必须保留失败重试和不丢数据的行为。

支持 `.json` 和 `.txt` 文件；跳过未下载的 iCloud 占位文件和修改后不足 60 秒的文件。去重依据是本地账本 `Logs/uploaded.json`，不是 Garmin Connect 中的记录。

## 编码风格与命名规范

使用 Python 3.11+、四空格缩进、PEP 8、`snake_case` 函数名和 `UPPER_CASE` 常量。`fit_weight.py` 仅使用标准库，并保持可被同目录的 `watcher.py` 导入。沿用现有文档字符串和注释风格，避免无关重构。

## 测试要求

仓库暂无自动化测试。先执行上文语法检查和 FIT 生成检查，再用真实文件验证 Garmin Connect 上传结果。若修改解析、去重或 FIT 生成逻辑，请使用标准库 `unittest` 新增 `tests/test_<模块名>.py`，执行：

```bash
./venv/bin/python -m unittest discover -s tests -v
```

## 提交与 Pull Request 规范

提交主题应简洁、使用中文祈使句，例如 `上传失败时保留源文件`。PR 需说明行为与配置变化、验证步骤和相关 issue；仅快捷指令或界面变化需要截图。

除非用户在当前对话中明确要求，否则不要执行 `git push`。本仓库的 GitHub 推送默认由用户手工完成。

## 安全与配置提示

不要提交 token、`Logs/`、`venv/`、`__pycache__/`、`scale-sync-mac.zip`、真实邮箱或体重数据，也不要用 `git add -f` 绕过 `.gitignore`。密码通过 `getpass` 输入；plist 模板保留 `you@example.com`，缓存的 token 只存放在 `~/.garminconnect/`。

`scripts/com.user.weighin.plist` 只是模板，路径为旧目录占位，部署前必须按 `docs/mac-setup.md` 修改。实际安装到 `~/Library/LaunchAgents/` 的 plist 不应提交。
