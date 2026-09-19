# Lightning 仓库 Push + GitHub Pages 一步清单

> 状态：**本地已提交，只差你登录 GitHub 推一次。** 下面每步都可复制执行。
> 仓库：`https://github.com/ooii166/Lightning`（公开，默认分支 `master`）
> 本地工作目录：`C:\Users\DELL\WorkBuddy\X推特\Lightning`

---

## ✅ 已完成（我做的，你不用动）
- 浅克隆 Lightning（公开仓库，无需鉴权）
- 把 `microgrants/ArcFlow/` 整目录拷入（含合约、前端、脚本、文档）
- 加了 `microgrants/ArcFlow/.gitignore`（排除 CDP 脚手架、vendored 编译器、`.env`）
- 仓库根加了 `.nojekyll`（让 Pages 直接当静态站服务，不跑 Jekyll）
- 本地提交：`feat: add ArcFlow microgrant ...`（18 个文件）

---

## 第 1 步：推送（需你的 GitHub 登录凭据）

```bash
cd "C:\Users\DELL\WorkBuddy\X推特\Lightning"
git push -u origin master
```

- 首次 push 时，本机 **Git Credential Manager 会弹窗**要你登录 GitHub（用浏览器授权即可）。
- 如果你习惯用 PAT：先 `git remote set-url origin https://<你的TOKEN>@github.com/ooii166/Lightning.git` 再 push。
- 若提示 `master` 与远程冲突（极少见），说明远程有你本地没有的提交，先 `git pull --rebase origin master` 再 push。

## 第 2 步：在 GitHub 网页开启 Pages

1. 打开 `https://github.com/ooii166/Lightning` → **Settings** → 左侧 **Pages**
2. **Source** 选 `Deploy from a branch`
3. **Branch** 选 `master`、**folder** 选 `/ (root)`
4. 点 **Save**
5. 等 1–2 分钟，GitHub 会给出网址：

```
公开演示页：https://ooii166.github.io/Lightning/microgrants/ArcFlow/web/index.html
```

> 说明：演示页在子路径 `microgrants/ArcFlow/web/` 下，因为 ArcFlow 是 Lightning 仓库里的子项目（根 README 是另一个「闪开来电」项目，保留未动）。

## 第 3 步：核对上链结果（可选但建议）

- 合约浏览器：https://explorer.testnet.arc.io/address/0xf004c40f0b8204c21991309A808dA2ee4895B9Eb
- 确认 `index.html` 打开后能读到合约状态（已连 Arc 测试网、合约地址已写入）。

---

## 以后要做的（决策权归你，我不代操作）

| 事项 | 命令/动作 | 备注 |
|---|---|---|
| 重新部署到**主网** | 改 `web/index.html`、`agent/arcflow_publisher.py` 的 RPC 回 `rpc.mainnet.arc.io`、CHAIN_ID 回 `5042`；用 `web/deploy.html` 重部署拿新地址 | 合约内部 `CHAIN` 字典的 `'arc':5042`（uint16 链代码）**别改**，会溢出 |
| 同步后续改动 | 在 `Lightning/` 里 `git add -A && git commit && git push` | 本地 ArcFlow 源在 `X推特/microgrants/ArcFlow`，改完再 cp 过来或直接在 `Lightning/microgrants/ArcFlow` 里改 |

---

## 测试网部署是干嘛用的（一句话）

测试网 = **免费沙盒 + 可查证的交付证据**：证明 ArcFlow 真能在 Arc 上跑，给微资助/开发者资助申请当"我真能构建"的实证。**它不直接给 Arc House 积分**（积分来自 community.arc.io 站内活动），是"真实贡献"这条线，不是积分农场。
