# 公网部署说明

本网站需要 Python/Flask 后端，不能只靠 GitHub Pages 托管。若要让别人不连接你家网络也能访问，把整个项目部署到公网平台即可。

## 方案一：GitHub + Render（推荐）

### 1. 上传到 GitHub

电脑未安装 Git 时也可以直接使用 GitHub 网页上传：

1. 登录 [github.com](https://github.com)，新建一个公开仓库，例如 `a-share-quant-workstation`。
2. 在仓库页面点击 `Add file` -> `Upload files`。
3. 把本目录中的全部文件拖入上传框，包括：
   - `app.py`
   - `requirements.txt`
   - `render.yaml`
   - `Dockerfile`
   - `data/`
   - `static/`
   - 其他 `.py`、`.md`、`.json` 文件
4. 提交上传。

如果安装了 Git，也可以直接使用：

```powershell
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/你的用户名/a-share-quant-workstation.git
git push -u origin main
```

### 2. 在 Render 创建 Web Service

1. 注册/登录 [render.com](https://render.com)，并连接 GitHub。
2. 点击 `New` -> `Blueprint` 或 `New` -> `Web Service`。
3. 选择刚上传的 GitHub 仓库。
4. 如果使用 Blueprint，Render 会自动读取 `render.yaml`。
5. 部署完成后，Render 会给出类似 `https://xxx.onrender.com` 的公网地址。

国内访问 Render 免费实例可能较慢；Railway 或其他服务可作为备选。

## 方案二：Railway

仓库已经包含 `railway.json`。在 Railway 中 New Project -> Deploy from GitHub repo 即可，启动命令会自动使用 `python app.py --host 0.0.0.0 --port $PORT --live`。

## 方案三：临时公网地址（无需 GitHub）

本机保持开机并能联网时，可安装 cloudflared 后运行：

```powershell
cloudflared tunnel --url http://127.0.0.1:8765
```

终端会生成一个 `*.trycloudflare.com` 临时地址。这个方案依赖本机在线，适合短期给朋友演示。

## 方案四：GitHub Codespaces（只注册 GitHub，不依赖 Render）

项目已包含 `.devcontainer/devcontainer.json`，会自动安装依赖并启动服务。

1. 把你的 GitHub 用户名和仓库名告诉我，或按方案一先把代码上传到 GitHub。
2. 在仓库页面点击 `Code` -> `Codespaces` -> 创建 Codespace。
3. 等待环境自动创建；`postCreateCommand` 会安装依赖，`postStartCommand` 会自动启动服务。
4. 打开底部的 `Ports` 面板，找到 `8765` 端口，把它设为 `Public`。
5. 复制端口面板中的公网地址，别人即可访问。

说明：Codespaces 免费配额有限，云端空间闲置后会被暂停；适合免费使用和测试，不适合作为 24 小时稳定生产站点。

## 部署注意事项

- 真实行情模式下，公网服务器会每 4-5 秒请求腾讯行情接口，请确认所部署平台允许出站 HTTP。
- 默认以 `--live` 启动，行情源失败时会保留最后一次快照。
- 免费平台可能在空闲后休眠，首次访问会稍慢。
- Render 免费 Web Service 不保证一直在线；正式长期使用可选择付费实例或国内云服务器。
