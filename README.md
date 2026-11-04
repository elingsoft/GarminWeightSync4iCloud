# 体重秤 → Garmin Connect 自动同步

> 体重秤称完 → iPhone 快捷指令 → iCloud Drive → Mac 常驻脚本 → 生成 FIT → 上传到 Garmin Connect，全程不用动手。

## 为什么需要这个项目

Garmin Connect 和 Apple 健康之间的数据流是**单向**的：Garmin 只会把数据**写进**健康，从不从健康里**读回**体重。也就是说，即使体重秤的数据已经进了 Apple 健康，Garmin Connect 里也不会出现。

本项目就是补上缺失的这一段：做一个“搬运工”，把健康里的最新体重以 FIT 文件的形式送进 Garmin Connect。

## 目录

- [功能详解](#功能详解)
- [需要什么：设备与条件](#需要什么设备与条件)
- [运行环境](#运行环境)
- [部署步骤](#部署步骤)
- [配置参考](#配置参考)
- [仓库结构](#仓库结构)
- [安全与隐私](#安全与隐私)
- [常见问题与排错](#常见问题与排错)
- [已知限制](#已知限制)
- [开源协议](#开源协议)

## 功能详解

### 全链路

```text
体重秤 → ScaleMe App → Apple 健康 → iPhone 快捷指令
  → iCloud Drive/WeightIn（一个 JSON 文件）
  → Mac 常驻脚本（launchd，每 60 秒扫描一次）
  → 生成 FIT 体重文件 → 上传到 Garmin Connect
  → 确认成功后删除源文件（删除会同步回 iCloud，手机上也消失）
```

### 1. 同步体重（FIT 方式）

- 同步内容是**体重**。FIT 文件里可以带体脂、肌肉、骨量等字段，但本项目只传体重，原因见[已知限制](#已知限制)。
- 体重文件由 `fit_weight.py` 生成：**只用 Python 标准库**，不依赖任何第三方 FIT 库。文件结构是 `file_id`（类型 = weight）+ 一条 `weight_scale` 消息（时间戳 + 体重），实测约 63 字节，体重精度 0.01 kg。
- 生成的文件经过 fitparse 回读验证，并在真实账号上实测上传成功。

### 2. 自动触发，不用动手

- **手机端**：iPhone 快捷指令在 ScaleMe 关闭时自动触发（也可改用早上闹钟停止时触发），读取健康里最新一条体重，写成 JSON 存进 iCloud Drive。
- **Mac 端**：launchd 任务每 60 秒唤醒一次 watcher，扫描 iCloud 文件夹，有新文件就处理。
- 整个链路不需要人值守，称完关 App 就行。

### 3. 登录与 Token 管理

- Mac 上只需交互登录**一次**：运行 `login_once.py`，按提示输入 Garmin 密码（通过 getpass 输入，**密码不存盘**）；账号开了双重验证会再提示输入 6 位码。
- 登录成功后，garminconnect 库把 token 缓存在 `~/.garminconnect/garmin_tokens.json`（文件权限 0600），watcher 此后上传不再需要密码，库会自动续期。
- **关键点**：garminconnect 0.3.x 只有显式传了 `tokenstore` 参数才会存取 token。裸 `login()` 只在内存里成功，磁盘上什么都不留，watcher 随后会报 `Username and password are required`。本项目的两个脚本都显式传了 tokenstore。
- Token 失效时 watcher 会报错并保留源文件，重跑一次 `login_once.py` 后，下一轮自动补传。

### 4. 上传机制

- 首选 garminconnect 库自带的 `upload_activity`。注意 0.3.20 的这个接口**只收文件路径**（字符串），不收字节流，而且要求文件带 FIT/TCX/GPX 后缀——所以 watcher 会先把 FIT 字节写成临时 `.fit` 文件再传，传完删除临时文件。
- 备用路径：如果库的上传接口不可用，watcher 会用缓存的 access token 直接 POST 到 Garmin 的 upload-service 接口。两条路径传的是同一个 FIT 文件。

### 5. 去重：同一天只传一条

- 按日期去重：同一天、体重差小于 0.05 kg 的文件视为同一条，重复文件**直接删除，不重复上传**。
- **去重依据是 Mac 本地的账本 `Logs/uploaded.json`，不是 Connect 里的内容**。所以即使你在 Connect 里手动删了某天的记录，账本里还记着的话，同一天的文件仍会被判为重复而删掉、不上传。想重测，必须连账本一起清掉。

### 6. 只有确认成功才删源文件

- 上传成功（服务器返回成功）后，watcher 才会删除 iCloud 里的源文件，并把这条记进账本。
- 任何失败（网络、登录、服务器拒绝、文件格式不对）都会保留源文件、记一条 FAILED 日志，下一轮继续重试，数据不会丢。

### 7. 时间窗口：只在指定时段运行

- `ACTIVE_WINDOWS` 可以限定每天的处理时段，例如只在早上 5:00–9:00 和晚上 20:00–22:00 运行。
- 窗口格式是（开始时，开始分，结束时，结束分），按 Mac 本地时间判断，结束时刻不含在内，支持跨午夜的窗口（例如 22:00–6:00）。
- 设为 `None` 就是全天运行。窗口外到达的文件不会丢，只是延迟到下一个窗口处理。
- launchd 本身仍每 60 秒唤醒一次，窗口判断在脚本开头做，窗口外直接退出，plist 不用改。

### 8. 文件同步保护

- 只处理 `.json` 和 `.txt` 文件：新版 iOS 的“保存文件”动作对文本输入会**强制补 `.txt` 后缀**，即使子路径写的是 `.json`，所以两种后缀都要接受。
- 跳过 `.icloud` 文件（还没从 iCloud 下载到本地的占位文件）。
- 文件修改时间不到 60 秒的跳过，等同步完成后再处理，避免读到一半的文件。

### 9. 体重解析容错

- 快捷指令把健康数值放进文本时，iOS 有时会带上单位（例如 `55.6 kg`、`55.6千克`），导致 JSON 里的体重不是纯数字。
- watcher 会从字符串里提取第一个数字，所以快捷指令只需发 `date` + `weight_kg` 两个字段就能工作。

### 10. 时间戳：真实时间或缺省 07:00

- JSON 里如果有 `measured_at`（ISO 8601 时间，例如 `2026-11-04T07:00:00+08:00`），就用它作为称重时间；FIT 里存 UTC，Connect 按本地时区显示。
- 如果没有 `measured_at`，缺省按当天 07:00（+08:00）计——这是按“早上称重”假设写的缺省值。所以如果你的快捷指令没发时间，Connect 里会显示 07:00，这不是上传失败。

### 11. 日志与状态文件

运行期文件统一放在项目级 `Logs/` 子目录，**不和代码混放**：

| 文件 | 内容 |
| --- | --- |
| `Logs/weighin.log` | watcher 的运行日志：uploaded / FAILED / deduped / watch dir not found |
| `Logs/weighin.err` | launchd 的 stderr（脚本崩溃时的 traceback 在这里） |
| `Logs/uploaded.json` | 去重账本：每个日期传过的体重、上传时间、服务器返回 |

launchd 的 stdout 指向 `/dev/null`（watcher 的日志是直接写文件的，不靠 stdout，所以不丢；手动跑脚本时终端照样能看到输出）。

## 需要什么：设备与条件

### 必备

| 项目 | 要求 | 说明 |
| --- | --- | --- |
| 体重秤 | 能把体重写入 Apple 健康的秤或 App | 本项目实测用 **ScaleMe（观我）+ 蚂蚁阿福联名秤**；只要体重能进健康，其他秤/App 同理 |
| iPhone | 能运行快捷指令，装有健康 App | 需要给快捷指令开健康读取权限 |
| Mac | macOS，能常开或在设定时段内在线 | 跑 watcher 和 launchd 任务；本项目实测用 MacBook Pro（Apple Silicon） |
| iCloud Drive | iPhone 和 Mac 登录**同一个 Apple ID**，并开启 iCloud Drive | 快捷指令和 Mac 靠它传文件 |
| Garmin Connect 账号 | 国际区（connect.garmin.com） | 中国区（connectus.garmin.cn）未测试 |
| 网络 | Mac 能访问互联网和 Garmin 服务器 | 上传需要；iCloud 同步也需要 |

### 核心前提（缺一不可）

1. **体重必须能进 Apple 健康**。这是整条链的起点：如果秤的 App 不写健康，快捷指令就读不到。
2. **手机触发时必须已解锁**。健康数据在锁屏时读不到，所以“ScaleMe 关闭时触发”这个自动化要求触发那一刻手机是解锁状态。
3. **Mac 和 iPhone 必须登录同一个 iCloud 账号**，否则 WeightIn 文件夹不会同步到 Mac 上。
4. **Mac 必须在设定的时间窗口内处于开机在线状态**，否则文件会等到下一个窗口（或 Mac 开机后）才处理。

## 运行环境

- **macOS**：近几年带 launchd 的版本均可（launchd 是 macOS 自带的常驻任务机制）。
- **Python**：3.11 或更高版本（实测 3.13）。建议用 venv，与系统 Python 隔开。
- **Python 包**：`garminconnect`（0.3.x，实测 0.3.20）、`curl_cffi`（garminconnect 的依赖，pip 会一并处理）。

```bash
python3 -m venv ~/GarminWeightSync/venv
~/GarminWeightSync/venv/bin/pip install garminconnect curl_cffi
```

- **目录结构**（以 `~/GarminWeightSync` 为例，你可以换成自己的路径，但 plist 里的路径必须同步改）：

```text
~/GarminWeightSync/
├── scripts/                 # 代码
│   ├── watcher.py           # 常驻扫描脚本
│   ├── login_once.py        # 一次性登录
│   ├── fit_weight.py        # FIT 生成器（必须和 watcher.py 同目录）
│   └── com.user.weighin.plist
├── docs/                    # 部署与快捷指令文档
│   ├── README.md
│   ├── mac-setup.md
│   └── shortcut-icloud.md
├── Logs/                    # 运行期文件（自动生成，不和代码混放）
│   ├── weighin.log
│   ├── weighin.err
│   └── uploaded.json
└── venv/                    # Python 虚拟环境

# 另外还有一处不在项目目录内：
#   ~/Library/LaunchAgents/com.user.weighin.plist   # launchd 任务（从仓库 scripts/ 复制过去）
```

## 部署步骤

下面以 `~/GarminWeightSync` 为项目目录、`WeightIn` 为 iCloud 文件夹名为例。请把示例里的邮箱和路径换成你自己的。更精简的 Mac 端部署清单见 `docs/mac-setup.md`。

### 第 1 步：准备 iCloud 文件夹

1. iPhone 上打开“文件”App → iCloud Drive，新建一个文件夹，名字必须是 **`WeightIn`**。
   - 注意：名字不要带前导空格（例如 `" WeightIn"` 是另一个文件夹，Mac 上会找不到）。
2. Mac 上确认系统设置 → iCloud → iCloud Drive 已打开。
3. 等 Mac 上出现这个目录（和 iPhone 同一个 Apple ID 才会同步）：

```bash
ls ~/Library/Mobile\ Documents/com~apple~CloudDocs/WeightIn
```

如果目录一直不出现，先在 iPhone 的文件 App 里往 WeightIn 存一个任意文件，确认同步通路是通的。

### 第 2 步：获取代码，建虚拟环境

```bash
# 把仓库 clone 到本地（或下载 zip 解压），假设放在 ~/GarminWeightSync
git clone https://github.com/elingsoft/GarminWeightSync4iCloud.git ~/GarminWeightSync
cd ~/GarminWeightSync
python3 -m venv venv
./venv/bin/pip install garminconnect curl_cffi
```

仓库已经包含 `scripts/` 目录，无需再手工复制脚本。`watcher.py` 会自动把自己所在的目录加入模块搜索路径，因此 `fit_weight.py` 必须留在同一目录，否则会报找不到模块。

### 第 3 步：一次性登录 Garmin（密码只输这一次，不存盘）

```bash
cd ~/GarminWeightSync/scripts
GARMIN_EMAIL=你的Garmin邮箱 ~/GarminWeightSync/venv/bin/python login_once.py
```

- 按提示输入密码（getpass 输入，屏幕不回显，**不写入任何文件**）。
- 账号开了双重验证，会再提示输入 6 位码。
- 成功后显示 `Login OK, tokens cached`，token 已存到 `~/.garminconnect/garmin_tokens.json`（权限 0600）。
- 此后 watcher 上传不再需要密码；token 由库自动续期。watcher 报错 token 失效时，重跑这一步即可，下一轮自动补传。

### 第 4 步：配置 watcher

watcher 的关键配置都在 `watcher.py` 顶部和环境变量里：

| 配置 | 位置 | 缺省值 | 说明 |
| --- | --- | --- | --- |
| `GARMIN_EMAIL` | 环境变量（plist 里也要设） | 空 | 你的 Garmin 登录邮箱 |
| `WEIGHIN_DIR` | 环境变量 | `~/Library/Mobile Documents/com~apple~CloudDocs/WeightIn` | 监听的 iCloud 文件夹 |
| `ACTIVE_WINDOWS` | `watcher.py` 常量 | `[(5, 0, 9, 0), (20, 0, 22, 0)]` | 每天的处理时段；改回 `None` 则全天运行 |
| `MIN_AGE_S` | `watcher.py` 常量 | `60` | 文件修改时间不到这么多秒就跳过（等同步完成） |
| `DEDUP_TOL` | `watcher.py` 常量 | `0.05` | 同一天体重差小于这么多 kg 视为同一条 |

改 `ACTIVE_WINDOWS` 时注意格式是（开始时，开始分，结束时，结束分），结束时刻不含在内；例如 `(5, 0, 9, 0)` 表示 5:00–9:00，9:00 整点已不在窗口内。

### 第 5 步：安装 launchd 常驻任务

```bash
# 把仓库 scripts/ 目录下的 plist 复制到 launchd 目录
cp ~/GarminWeightSync/scripts/com.user.weighin.plist ~/Library/LaunchAgents/

# 编辑 ~/Library/LaunchAgents/com.user.weighin.plist，确认三件事：
#   1. ProgramArguments 里的 Python 路径和 watcher.py 路径是你机器上的真实路径
#   2. WorkingDirectory 是 scripts/ 目录
#   3. EnvironmentVariables 里的 GARMIN_EMAIL 换成你的 Garmin 邮箱
#   （模板里是占位符 you@example.com，不改的话登录会失败）

# 加载并验证
launchctl load ~/Library/LaunchAgents/com.user.weighin.plist
launchctl list | grep weighin
```

- `launchctl list` 应该显示 `- 0 com.user.weighin`。**如果显示 `- 78`，表示任务配置错误（EX_CONFIG），最常见的原因是 plist 里的路径和实际布局对不上**——例如 Python 或脚本路径写的是旧目录。先对着第 5 步的三件事逐项核对，改完后 `unload` 再 `load` 才会生效。
- 此后每 60 秒扫描一次；`Logs/weighin.log` 里会出现运行记录。

### 第 6 步：建 iPhone 快捷指令

#### 触发（二选一）

- 首选：ScaleMe 关闭时触发。注意触发那一刻手机必须已解锁，否则健康读不到。
- 备选：早上闹钟停止时触发。

#### 动作（按顺序）

1. **查找健康样本**：类型选“体重”，排序方式选“开始日期”、顺序选“最新的排最前”，限制打开、获取 1 项。
2. **获取健康样本的详细信息** → 开始日期。
3. **获取健康样本的详细信息** → 值。
4. **格式化日期**：输入选第 2 步的开始日期，日期格式选自定义，填 `yyyy-MM-dd`。
5. **文本**，拼成 JSON（用变量拼，不要手写死数字）：

```json
{"date":"2026-11-04","weight_kg":55.6}
```

6. **保存文件**：把文本存到 `WeightIn`，询问保存位置**关**，如果文件存在则覆盖**开**，子路径填 `weighin-` + 第 4 步的日期 + `.json`。

#### 可选：带上真实称重时间

如果想让 Connect 显示真实称重时间而不是缺省 07:00，再加一步：

1. 再加一个**格式化日期**动作，输入同样选开始日期，格式选自定义，填 `yyyy-MM-dd'T'HH:mm:ssZZZZZ`。
2. 文本改成：

```json
{"date":"2026-11-04","weight_kg":55.6,"measured_at":"2026-11-04T07:00:00+08:00"}
```

#### iOS 快捷指令的几个坑（实测经验）

- **保存文件会强制补 `.txt` 后缀**：新版 iOS 对文本输入保存时，即使子路径写的是 `.json`，实际落盘也常是 `weighin-2026-11-04.txt`。watcher 同时接受 `.json` 和 `.txt`，所以快捷指令侧不用改。
- **两个格式化日期的输出重名**：第 4 步和“带时间”那步的输出都叫“格式化后的日期”。往文本里插变量时，排在后面的那个就是新加的（带时间的）；看文本预览区分：带 `T` 和 `+08:00` 的就是日期时间那个。
- **变量选错**：新加动作时输入框可能自动填了上一步的输出；要点输入框的 token → 清除变量 → 重新选开始日期。
- **文件名栏误设**：保存文件的“子路径/文件名”栏如果填成了 JSON 文本本身，会导致文件名就是一串 JSON、内容为空。文件名栏只填 `weighin-日期.json` 这种形式。
- **健康权限**：快捷指令第一次读健康时会弹权限，必须允许；且触发时手机需已解锁。

### 第 7 步：联调一次真实称重

1. 实称一次（或触发一次快捷指令），确认 WeightIn 文件夹里出现当天的文件。
2. 等 1–2 分钟（iCloud 同步 + 60 秒文件龄 + 60 秒扫描周期）。
3. 查三处：
   - Garmin Connect → 健康统计 → 体重，出现新记录；
   - `Logs/weighin.log` 里出现 `uploaded …; source file deleted`；
   - WeightIn 文件夹里的源文件已消失。
4. 如果文件一直没删：看 `Logs/weighin.log` 的报错，对照[常见问题与排错](#常见问题与排错)。

### 第 8 步：日常使用

- 此后什么都不用管：称重 → 关 ScaleMe → 记录自动进 Connect。
- 换秤或换 App 时，只要新来源能把体重写进健康，链路其余部分不用动。
- 想改处理时段，改 `watcher.py` 的 `ACTIVE_WINDOWS` 即可，launchd 不用重载（每次唤醒都会重新读脚本）。

## 配置参考

### 环境变量

| 变量 | 用途 | 设置位置 |
| --- | --- | --- |
| `GARMIN_EMAIL` | Garmin 登录邮箱 | `login_once.py` 运行时、plist 的 `EnvironmentVariables`、手动跑 watcher 时 |
| `GARMIN_PASSWORD` | 仅手动调试用 | 不推荐设置；正常流程用 token，不用密码 |
| `WEIGHIN_DIR` | 覆盖缺省的监听目录 | 手动跑 watcher 或 plist 的 `EnvironmentVariables` |

### watcher.py 常量

| 常量 | 缺省值 | 说明 |
| --- | --- | --- |
| `ACTIVE_WINDOWS` | `[(5, 0, 9, 0), (20, 0, 22, 0)]` | 处理时段；`None` = 全天 |
| `MIN_AGE_S` | `60` | 文件未满这么多秒不处理 |
| `DEDUP_TOL` | `0.05` | 去重容差（kg） |
| `WATCH_DIR` | iCloud WeightIn 路径 | 可用 `WEIGHIN_DIR` 环境变量覆盖 |
| `LOG_DIR` | 项目级 `Logs/` | 日志和账本目录，脚本自动创建 |

### 文件格式

快捷指令发来的 JSON，字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `date` | 是 | `YYYY-MM-DD` 格式的日期 |
| `weight_kg` | 是 | 体重，数字或带单位的字符串（例如 `"55.6 kg"` 也能解析） |
| `measured_at` | 否 | ISO 8601 时间；缺省按当天 07:00（+08:00）计 |

校验规则：日期必须是 10 位 `YYYY-MM-DD`，体重必须在 20–300 kg 之间，否则记 FAILED 并保留文件。

## 仓库结构

```text
.
├── README.md                  # 项目总览
├── AGENTS.md                  # 仓库协作与开发规则
├── LICENSE                    # MIT 协议
├── scripts/
│   ├── watcher.py             # 常驻扫描脚本（核心）
│   ├── fit_weight.py          # FIT 体重文件生成器（纯标准库）
│   ├── login_once.py          # 一次性 Garmin 登录（种子 token）
│   └── com.user.weighin.plist # launchd 任务模板（部署前修改路径和邮箱）
├── docs/
│   ├── README.md              # 文档索引
│   ├── mac-setup.md           # Mac 端部署与排错（以此为准）
│   └── shortcut-icloud.md     # iPhone 快捷指令说明
├── Logs/                      # 运行期文件（本地生成，不提交）
└── venv/                      # Python 虚拟环境（本地生成，不提交）
```

推荐部署使用 `scripts/` 下的 `watcher.py`、`fit_weight.py`、`login_once.py` 和 `com.user.weighin.plist`。`scale-sync-mac.zip` 是本机历史归档，已被 `.gitignore` 排除，不作为部署来源。

## 安全与隐私

- **密码永不存盘**：密码只在 `login_once.py` 运行时通过 getpass 输入一次，不写入任何文件、日志或代码。不要把密码写进 plist、脚本或环境变量文件。
- **Token 文件权限**：`~/.garminconnect/garmin_tokens.json` 由库以 0600 权限保存（仅本人可读写）。不要把它发给别人或提交到公开仓库。
- **数据去向**：体重数据只从你的 iPhone 经 iCloud 到你的 Mac，再由 Mac 直接上传到 Garmin，不经过任何第三方服务器。本项目没有服务端组件（已废弃的 Cloudflare / InstaBox 路线除外，不要启用它们）。
- **公开仓库前检查清单**（提交前逐项确认）：
  - [ ] 没有提交 `~/.garminconnect/` 下的任何文件
  - [ ] 没有提交 `Logs/`（里面有你的体重记录和上传返回）
  - [ ] plist 里的 `GARMIN_EMAIL` 是占位符，不是你的真实邮箱
  - [ ] 没有提交 `__pycache__`、`.pyc`、个人路径或真实体重数据
  - [ ] 确认 `.gitignore` 已排除：`Logs/`、`venv/`、`__pycache__/`、`*.pyc`、`.garminconnect/`、`scale-sync-mac.zip`

## 常见问题与排错

### launchd 任务状态一直是 78（EX_CONFIG），日志为空

**原因**：任务配置错误，launchd 一次都没能把脚本拉起来。最常见的是 plist 里的路径和实际布局对不上（例如 Python 或脚本路径写的是旧目录）。

**排查**：

```bash
cat ~/Library/LaunchAgents/com.user.weighin.plist
plutil -lint ~/Library/LaunchAgents/com.user.weighin.plist
launchctl print gui/$(id -u)/com.user.weighin | head -40
```

逐项核对 `ProgramArguments`（Python 路径、脚本路径）、`WorkingDirectory`、`GARMIN_EMAIL` 是否都是真实值。改完后必须 `unload` 再 `load` 才会生效；只改文件不重载，跑的还是旧配置。

### watcher 报 `Username and password are required`

**原因**：token 没存到磁盘。garminconnect 0.3.x 只有显式传了 `tokenstore` 才会存取 token，裸 `login()` 只在内存里成功。

**修复**：确认 `login_once.py` 和 `watcher.py` 都传了 `tokenstore="~/.garminconnect/garmin_tokens.json"`，然后重跑一次 `login_once.py`，再用 `ls -la ~/.garminconnect/` 确认 `garmin_tokens.json` 已生成（应为 0600 权限、非零大小）。

### watcher 报 `upload_activity() takes 2 positional arguments but 3 were given`

**原因**：0.3.20 的 `upload_activity` 只收一个文件路径参数，不收字节流。本项目已修复：先把 FIT 写成临时 `.fit` 文件再传路径。

**修复**：确认你用的 `watcher.py` 是仓库最新版（里面有 `NamedTemporaryFile(suffix=".fit")` 那段）。

### 文件一直在 WeightIn 里，迟迟不处理

按顺序查：

1. **在不在时间窗口内**：`ACTIVE_WINDOWS` 之外的时间，脚本会直接退出，文件等到下一窗口才处理，这是正常的。
2. **文件有没有真正下载到本地**：Finder 里文件如果带云下载图标，表示内容还在云端、本地只有占位。右键“立即下载”，或在系统设置 → Apple ID → iCloud → iCloud Drive 里关掉“优化 Mac 储存空间”，让文件常驻本地。
3. **launchd 任务是不是好的**：`launchctl list | grep weighin`，状态应为 `0`；如果是 `78`，按上面那条排查。
4. **文件是不是太新**：修改时间不到 60 秒的文件会跳过，等下一轮。

### 删了 Connect 里的记录，重测还是不上传

**原因**：去重看的是本地账本 `Logs/uploaded.json`，不是 Connect 里的内容。删 Connect 记录不重置去重。

**修复**：重测前连账本一起清：删 Connect 记录 + 删 `Logs/uploaded.json`（它会在下次上传成功时自动重建）。注意：正常使用时不要删账本，否则同一天会重复上传。

### Connect 里显示的时间是 07:00，和实际称重时间不一致

**原因**：快捷指令没发 `measured_at`，watcher 按缺省值当天 07:00 计。这不是上传失败。

**修复**：按[第 6 步“带上真实称重时间”](#可选带上真实称重时间)给快捷指令加一个格式化日期动作。

### 快捷指令生成的文件内容是空的，或文件名就是一串 JSON

**原因**：保存文件动作的字段填错了——JSON 文本被填进了文件名栏，而不是内容栏。

**修复**：内容栏放 JSON 文本，文件名栏只填 `weighin-日期.json` 这种形式；并确认“如果文件存在则覆盖”已打开。

### 快捷指令读不到体重（值为空）

**原因**：通常是健康权限没给，或健康里还没有新的体重记录（秤的 App 还没写进来）。

**修复**：确认快捷指令的健康权限已允许；先实称一次、确认健康里出现新体重后，再触发快捷指令。

### token 失效

**现象**：`Logs/weighin.log` 里出现登录失败，源文件被保留。

**修复**：重跑一次 `login_once.py`（按提示输密码和双重验证码），下一轮自动补传，不用手动处理积压文件。

## 已知限制

- **只同步体重**：ScaleMe 只把体重写进健康，体脂写不进；所以本项目同步的只有体重，体脂、肌肉等指标不在覆盖范围。
- **旧记录拿不回**：秤一旦把某条记录给过一个 App，就不再提供给其他 App。切换到 ScaleMe 之前的旧记录只能手动补录，本项目不做历史回补。
- **依赖 iCloud 同步**：iPhone 和 Mac 之间的文件靠 iCloud Drive；同步延迟或未下载到本地都会延迟处理（文件本身不会丢）。
- **依赖 Mac 在线**：Mac 必须在设定时段内开机在线；关机期间的文件会等到下次开机 + 窗口内才处理。
- **依赖 ScaleMe 写健康**：如果 ScaleMe 变更行为（例如不再写健康），链路起点就会断，需要换一个能写健康的来源。
- **Garmin 账号分区**：实测用国际区账号；中国区账号未测试。
- **窗口外延迟**：窗口外到达的文件会延迟到下一窗口，这是有意设计，不是故障。

## 开源协议

本项目采用 MIT 协议开源（见仓库根目录的 `LICENSE` 文件；如果你 fork 后想换协议，改 `LICENSE` 并同步更新本节即可）。

---

*实测环境：iPhone + ScaleMe + 蚂蚁阿福联名秤 → MacBook Pro（Apple Silicon，macOS）→ Garmin Connect 国际区。不同 iOS / macOS 版本的快捷指令与系统设置界面可能略有差异，请以你设备的实际界面为准。*
