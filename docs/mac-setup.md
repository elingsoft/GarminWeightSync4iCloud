# Mac 端搭建（快捷指令 → iCloud → Mac → Garmin）

本文件是 Mac 端部署与排错的唯一说明。

## 链路
ScaleMe → 健康 → 快捷指令（存 JSON 到 iCloud Drive/WeightIn）→
Mac 常驻脚本（每 60 秒扫一次）→ 转 FIT → 传 Garmin → 成功后删源文件。

## 1. 准备文件夹
- iPhone：文件 App → iCloud Drive 里建一个 `WeightIn` 文件夹。
- Mac：系统设置 → iCloud → iCloud Drive 已打开；等 `~/Library/Mobile
  Documents/com~apple~CloudDocs/WeightIn` 出现（和 iPhone 同一账号）。

## 2. 获取代码并安装依赖
```bash
git clone https://github.com/elingsoft/GarminWeightSync4iCloud.git ~/GarminWeightSync
cd ~/GarminWeightSync
python3 -m venv venv
./venv/bin/pip install garminconnect curl_cffi
```

代码已经在仓库的 `scripts/` 目录，不需要再从压缩包复制。

## 3. 一次性登录（密码只输这一次，不存盘）
```bash
cd ~/GarminWeightSync
GARMIN_EMAIL=你的Garmin邮箱 ./venv/bin/python scripts/login_once.py
```
按提示输密码；开了双重验证就再输一次 6 位码。
成功后 token 由 garminconnect 库缓存在 `~/.garminconnect/garmin_tokens.json`，
后续由库自动续期。

## 4. 设常驻
```bash
cp ~/GarminWeightSync/scripts/com.user.weighin.plist ~/Library/LaunchAgents/
```

编辑 `~/Library/LaunchAgents/com.user.weighin.plist`，至少核对：
- `ProgramArguments`：Python 和 `scripts/watcher.py` 的绝对路径。
- `WorkingDirectory`：`~/GarminWeightSync/scripts`。
- `GARMIN_EMAIL`：真实的 Garmin 邮箱，替换 `you@example.com`。
- 日志路径：建议指向 `~/GarminWeightSync/Logs/`。

```bash
launchctl load ~/Library/LaunchAgents/com.user.weighin.plist
launchctl list | grep weighin
```

状态应为 `- 0 com.user.weighin`。此后每 60 秒扫描一次，运行日志在
`~/GarminWeightSync/Logs/weighin.log`；上传失败会保留源文件并重试。

## 5. 快捷指令
按同目录的 [`shortcut-icloud.md`](shortcut-icloud.md) 建：触发（ScaleMe 关闭或早上闹钟停止）→
读健康最新体重 → 存 `weighin-<日期>.json` 到 iCloud Drive/WeightIn。
注意：健康数据锁屏时读不到，触发时手机需已解锁。

## 6. 联调一次真实称重
1. 实称一次，等 1–2 分钟。
2. 查三处：Garmin Connect 网页 → Health Stats → Weight 有新记录；
   `Logs/weighin.log` 有 `uploaded` 字样；WeightIn 文件夹里的源文件已消失。
3. 若日志报错，按报错处理；token 失效时重跑第 3 步的 `login_once.py`。

## 失败处理
- 上传失败：源文件保留，下一轮重试，日志记原因。
- token 失效：watcher 报错并保留文件，重跑 `login_once.py` 后自动补传。
- 同一天重复文件：按日期去重（体重差 < 0.05 kg 视为同一条），
  重复文件直接删除，不会重复上传。
- 运行时段：默认只在 5:00–9:00 和 20:00–22:00 处理；窗口外文件会等待。
