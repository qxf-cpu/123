# 启恒物流智能算价助手 — UI 改版

Gradio 界面视觉升级：独立样式表、三栏布局、导航高亮、更克制的配色与 typography。

## 本地运行（预览）

```bash
pip install -r requirements.txt
python app.py
```

浏览器打开 `http://127.0.0.1:7860`。

## 合并到你现有 xkagent 项目

1. 复制 `ui_styles.css` 到与 `app.py` 同级目录。
2. 用本仓库 `app.py` 替换原文件，或对照 diff 合并：
   - 删除内联 `CSS = """..."""`，改为读取 `ui_styles.css`
   - 顶栏 / 侧栏 / 右侧品牌栏布局
   - `_nav_updates()` 与导航按钮 `elem_classes`
   - `demo.launch(..., theme=theme, css=CSS)`（Gradio 6）
3. 保留你原有的 `agent_core.py`、`zt_*`、`chat_db.py` 等业务模块（本仓库仅为预览提供了 stub）。
