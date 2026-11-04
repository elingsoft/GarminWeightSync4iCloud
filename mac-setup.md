# Mac 端搭建（快捷指令 → iCloud → Mac → Garmin）

## 链路
ScaleMe → 健康 → 快捷指令（存 JSON 到 iCloud Drive/WeighIn）→
Mac 常驻脚本（每 60 秒扫一次）→ 转 FIT → 传 Garmin → 成功后删源文件。

## 1. 准备文件夹
- iPhone：文件 App → iCloud Drive 里建一个 `WeighIn` 文件夹。
- Mac：系统设置 → iCloud → iCloud Drive 已打开；等 `~/Library/Mobile
  Documents/com~apple~CloudDocs/WeighIn` 出现（和 iPhone 同一账号）。

## 2. 装脚本
```bash
cd /Users/elingsoft/GarminWeightSync
# watcher.py、login_once.py、fit_weight.py 已在此目录
python3 -m venv /Users/elingsoft/GarminWeightSync/venv
/Users/elingsoft/GarminWeightSync/venv/bin/pip install garminconnect curl_cffi
```

## 3. 一次性登录（密码只输这一次，不存盘）
```bash
GARMIN_EMAIL=你的Garmin邮箱 /Users/elingsoft/GarminWeightSync/venv/bin/python login_once.py
```
按提示输密码；开了双重验证就再输一次 6 位码。
成功后 token 由 garminconnect 库自己缓存并自动续期。

## 4. 设常驻
```bash
# 把 com.user.weighin.plist 放到 ~/Library/LaunchAgents/，并改两处：
#   - /Users/elingsoft 换成你自己的用户名
#   - GARMIN_EMAIL 换成你的 Garmin 邮箱
launchctl load ~/Library/LaunchAgents/com.user.weighin.plist
```
此后每 60 秒扫一次 WeighIn 文件夹；日志在
`~/Library/Logs/weighin.log`，失败会记在里面并保留源文件重试。

## 5. 快捷指令
按 `shortcut-icloud.md` 建：触发（ScaleMe 关闭 或 早上闹钟停止）→
读健康最新体重 → 存 `weighin-<日期>.json` 到 iCloud Drive/WeighIn。
注意：健康数据锁屏时读不到，触发时手机需已解锁。

## 6. 联调一次真实称重
1. 实称一次，等 1–2 分钟。
2. 查三处：Garmin Connect 网页 → Health Stats → Weight 有新记录；
   Mac 上 `weighin.log` 有 uploaded 字样；WeighIn 文件夹里的源文件已删。
3. 若 `weighin.log` 报错，把报错贴给助手；若报 token 失效，
   重跑第 3 步的 login_once.py 即可。

## 失败处理
- 上传失败：源文件保留，下一轮重试，日志记原因。
- token 失效：watcher 报错并保留文件，重跑 login_once.py 后自动补传。
- 同一天重复文件：按日期去重（体重差 < 0.05 kg 视为同一条），
  重复文件直接删除，不会重复上传。
