# Repository Guidelines

## 项目结构与模块组织

- `scripts/` 是当前实现：`watcher.py` 扫描并处理称重文件，`fit_weight.py` 生成 FIT，`login_once.py` 缓存 Garmin token，`com.user.weighin.plist` 是 launchd 模板。
- `weighin/` 是旧版打包副本。日常修改以 `scripts/` 为准；仅在明确要求同步归档时改动 `weighin/`。
- `Logs/` 保存运行日志和去重账本（`weighin.log`、`weighin.err`、`uploaded.json`），不得提交。
- `venv/` 是本地虚拟环境。部署以 `README.md` 为准，`mac-setup.md` 与 `shortcut-icloud.md` 为辅助说明。

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

## 架构与数据流

iPhone 快捷指令把 JSON 写入 iCloud Drive 的 `WeightIn`；`watcher.py` 按日期和体重去重，生成 FIT 并上传，只有确认成功后才删除源文件。修改时必须保留失败重试和不丢数据的行为。

## 编码风格与命名规范

使用 Python 3.11+、四空格缩进、PEP 8、`snake_case` 函数名和 `UPPER_CASE` 常量。`fit_weight.py` 仅使用标准库，并保持可被同目录的 `watcher.py` 导入。沿用现有文档字符串和注释风格，避免无关重构。

## 测试要求

仓库暂无自动化测试。先执行上文语法检查和 FIT 生成检查，再用真实文件验证 Garmin Connect 上传结果。若修改解析、去重或 FIT 生成逻辑，请新增 `tests/test_<模块名>.py` 测试并注明执行命令。

## 提交与 Pull Request 规范

当前目录没有可用的 Git 历史，无法沿用既有提交格式。提交主题应简洁、使用祈使句，例如 `上传失败时保留源文件`。PR 需说明行为与配置变化、验证步骤和相关 issue；仅快捷指令或界面变化需要截图。

## 安全与配置提示

不要提交 token、`Logs/`、`venv/`、`__pycache__/`、真实邮箱或体重数据。密码通过 `getpass` 输入；plist 模板保留 `you@example.com`，缓存的 token 只存放在 `~/.garminconnect/`。
