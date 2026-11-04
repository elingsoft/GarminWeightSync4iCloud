# iPhone 快捷指令：称重后存文件到 iCloud（Mac 路线）

前提：ScaleMe 已写体重到健康；iCloud Drive 里已有 `WeighIn` 文件夹；
Mac 上 watcher 已常驻（见 [mac-setup.md](mac-setup.md)）。

## 触发（二选一）
- 首选：打开 App → ScaleMe → 关闭时（需手机已解锁）。
- 备选：早上闹钟停止时。

## 动作
1. 「查找健康样本」：类型 体重，排序 最新，数量 1。
2. 「获取健康样本的详细信息」：值（kg）、开始日期。
3. 「文本」：拼成 JSON（日期取开始日期的 yyyy-MM-dd，时间取完整 ISO）：
   `{"date":"2026-11-04","weight_kg":55.6,"measured_at":"2026-11-04T07:00:00+08:00"}`
   （日期和体重用上一步的变量拼，不要手写死数字。）
4. 「存储文件」：内容为上一步的文本，路径
   `iCloud Drive/WeighIn/weighin-2026-11-04.json`（文件名里的日期
   同样用变量），打开「覆盖」。
5. 失败时弹通知（「存储文件」动作本身失败时 iOS 会提示；也可另加
   「如果」判断文件是否存在来确认）。

## 联调
1. 实称一次，确认 WeighIn 文件夹里出现当天的 JSON。
2. 等 1–2 分钟：Mac 的 watcher 会处理；成功后源文件自动删除，
   Garmin Connect 体重页出现记录。
3. 若文件一直没删：看 Mac 上 `~/GarminWeightSync/Logs/weighin.log` 的报错。
