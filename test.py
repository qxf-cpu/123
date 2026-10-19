"""
启恒物流智能算价助手 — Gradio 界面（单文件可拷贝）
用法：与 agent_core / chat_db / zt_* 等同目录，执行 python test.py
样式已内联在 CSS 变量中，无需 ui_styles.css。
"""

import os
import re
import threading
import uuid
import json

import gradio as gr
from agent_core import XkChatAgent
from chat_db import (
    init_db,
    save_messages,
    load_history,
    clear_history,
    get_all_sessions,
    set_session_title,
    delete_all_sessions,
    search_sessions,
    rename_session,
)

try:
    from zt_bridge import run_zt_pricing, ZT_EXCEL
    from zt_input import (
        parse_text_order,
        write_orders_to_excel,
        order_markdown,
        find_missing_required,
        address_looks_incomplete,
    )
    from zt_vision import extract_orders_via_vision, vision_config_summary

    _ZT_OK = True
except Exception as _zt_e:
    _ZT_OK = False
    print(f"[警告] 中通算价桥接加载失败：{_zt_e}")

    def vision_config_summary():
        return "（zt_vision 模块未加载）"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.jpg")
CSS = '''
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

:root {
  --font-sans: 'Noto Sans SC', 'DM Sans', system-ui, sans-serif;
  --bg-page: #eef1f6;
  --bg-elevated: #ffffff;
  --bg-muted: #f6f8fb;
  --border: #e2e8f0;
  --border-strong: #cbd5e1;
  --text: #1e293b;
  --text-muted: #64748b;
  --text-soft: #94a3b8;
  --accent: #e07b24;
  --accent-hover: #c96812;
  --accent-soft: #fff4e8;
  --accent-ring: rgba(224, 123, 36, 0.25);
  --success: #059669;
  --success-soft: #ecfdf5;
  --danger: #dc2626;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 8px 24px rgba(15, 23, 42, 0.08);
  --shadow-lg: 0 16px 40px rgba(15, 23, 42, 0.1);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
}

* {
  font-family: var(--font-sans) !important;
}

.gradio-container {
  max-width: 100% !important;
  width: 100% !important;
  padding: 16px 20px 24px !important;
  background: radial-gradient(1200px 600px at 10% -10%, #fff7ed 0%, transparent 55%),
    radial-gradient(900px 500px at 100% 0%, #e0f2fe 0%, transparent 45%),
    var(--bg-page) !important;
}

footer {
  visibility: hidden;
}

.app-shell {
  gap: 16px !important;
}

#title-bar {
  align-items: center;
  justify-content: space-between !important;
  margin-bottom: 4px;
  padding: 18px 24px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

#title-bar .title-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

#title-bar h1 {
  color: var(--text) !important;
  margin: 0 !important;
  font-size: 22px !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em;
}

#title-bar .title-sub {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

#title-bar .title-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-hover);
  font-size: 12px;
  font-weight: 600;
  border: 1px solid #fde6c8;
  white-space: nowrap;
}

#side-nav {
  min-width: 248px !important;
  max-width: 280px !important;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 18px 16px 16px;
  box-shadow: var(--shadow-sm);
}

.side-nav-head {
  padding: 4px 8px 14px;
  margin-bottom: 8px;
  border-bottom: 1px dashed var(--border);
}

.side-nav-head .sn-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.side-nav-head .sn-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

#nav-btns {
  gap: 6px !important;
}

#nav-btns button {
  width: 100% !important;
  text-align: left !important;
  justify-content: flex-start !important;
  padding: 11px 14px !important;
  border-radius: var(--radius-sm) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  background: var(--bg-muted) !important;
  border: 1px solid transparent !important;
  color: var(--text-muted) !important;
  box-shadow: none !important;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

#nav-btns button:hover {
  background: var(--accent-soft) !important;
  border-color: #fde6c8 !important;
  color: var(--accent-hover) !important;
}

#nav-btns button.nav-active {
  background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%) !important;
  border-color: transparent !important;
  color: #fff !important;
  box-shadow: 0 4px 14px var(--accent-ring) !important;
}

#side-panel-wrap {
  margin-top: 14px;
  max-height: calc(100vh - 320px);
  overflow: auto;
  padding-right: 4px;
}

#side-panel-wrap::-webkit-scrollbar {
  width: 6px;
}

#side-panel-wrap::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 999px;
}

.panel {
  padding: 2px 4px;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 12px;
  padding-left: 0;
  border-left: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-title::before {
  content: '';
  width: 4px;
  height: 16px;
  border-radius: 2px;
  background: linear-gradient(180deg, #f59e0b, #ea580c);
}

.panel p {
  margin: 8px 0;
  line-height: 1.75;
  font-size: 13px;
  color: var(--text-muted);
}

.hist-search-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.hist-search-input {
  flex: 1;
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  outline: none;
  background: var(--bg-muted);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.hist-search-input:focus {
  border-color: var(--accent);
  background: #fff;
  box-shadow: 0 0 0 3px var(--accent-ring);
}

.hist-search-btn {
  padding: 9px 14px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--text);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}

.hist-search-btn:hover {
  background: #0f172a;
}

.hist-clearall-row {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--border);
}

.hist-clearall-btn {
  width: 100%;
  padding: 10px 16px;
  border: 1px solid #fecaca;
  border-radius: var(--radius-sm);
  background: #fef2f2;
  color: var(--danger);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}

.hist-clearall-btn:hover {
  background: #fee2e2;
}

.hist-item {
  position: relative;
  padding: 10px 36px 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  font-size: 13px;
  cursor: pointer;
  margin-bottom: 4px;
}

.hist-item:hover {
  background: var(--bg-muted);
  border-color: var(--border);
}

.hist-main {
  display: block;
}

.hist-meta {
  color: var(--text-soft);
  font-size: 11px;
  display: block;
  margin-top: 2px;
}

.hist-more {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 18px;
  color: var(--text-soft);
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.hist-more:hover {
  background: var(--accent-soft);
  color: var(--accent);
}

.hist-dropdown {
  display: none;
  position: absolute;
  right: 8px;
  top: 100%;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
  min-width: 108px;
  z-index: 1000;
  overflow: hidden;
}

.hist-dropdown a {
  display: block;
  padding: 8px 14px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 13px;
}

.hist-dropdown a:hover {
  background: var(--bg-muted);
  color: var(--text);
}

.hist-dropdown a.danger {
  color: var(--danger);
}

.dialog-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  z-index: 9999;
  justify-content: center;
  align-items: center;
}

.dialog-box {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  min-width: 360px;
  max-width: 90%;
  overflow: hidden;
}

.dialog-header {
  padding: 16px 20px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  border-bottom: 1px solid var(--border);
}

.dialog-body {
  padding: 20px;
  font-size: 14px;
  color: var(--text-muted);
}

.dialog-body p {
  margin: 8px 0;
}

.dialog-highlight {
  font-weight: 600;
  color: var(--text);
}

.dialog-warning {
  color: var(--danger);
  font-size: 13px;
}

.dialog-footer {
  padding: 12px 20px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid var(--border);
  background: var(--bg-muted);
}

.dialog-btn {
  padding: 8px 18px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  cursor: pointer;
  font-weight: 600;
}

.dialog-btn.cancel {
  background: #fff;
  color: var(--text-muted);
  border: 1px solid var(--border);
}

.dialog-btn.confirm {
  background: var(--text);
  color: #fff;
}

.dialog-btn.confirm.danger {
  background: var(--danger);
}

.dialog-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}

.dialog-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-ring);
}

#chat-panel {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 18px 18px 16px;
  box-shadow: var(--shadow-sm);
  flex: 1 !important;
  min-width: 0 !important;
}

#chat-panel .chatbot,
#chat-panel [class*='chatbot'] {
  width: 100% !important;
  border: none !important;
  background: transparent !important;
}

#answer-area {
  background: linear-gradient(180deg, #fafbfd 0%, #f4f7fb 100%);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 14px 8px;
  margin-bottom: 14px;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-soft);
  margin-bottom: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

#answer-area .message.user,
#answer-area [data-testid='user'] {
  background: #fff !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px 14px 4px 14px !important;
}

#answer-area .message.bot,
#answer-area [data-testid='bot'],
#answer-area .chatbot .message-wrap.bot {
  background: linear-gradient(135deg, #fff9f2 0%, #fff4e8 100%) !important;
  border: 1px solid #fde6c8 !important;
  border-radius: 14px 14px 14px 4px !important;
  box-shadow: var(--shadow-sm) !important;
}

#answer-area blockquote {
  background: rgba(255, 255, 255, 0.65) !important;
  border-left: 3px solid var(--accent) !important;
  margin: 10px 0 !important;
  padding: 8px 14px !important;
  color: #7c6a56 !important;
  border-radius: 0 8px 8px 0;
}

#input-area {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
}

#input-area .textbox textarea,
#input-area textarea {
  background: var(--bg-muted) !important;
  border-color: var(--border) !important;
  border-radius: var(--radius-sm) !important;
  min-height: 88px !important;
  font-size: 14px !important;
}

#input-area .textbox textarea:focus,
#input-area textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-ring) !important;
}

.upload-row label {
  font-size: 12px !important;
  font-weight: 600 !important;
  color: var(--text-muted) !important;
}

#action-row {
  gap: 8px !important;
  margin-top: 4px !important;
}

#submit-btn {
  border-radius: var(--radius-sm) !important;
  background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 14px var(--accent-ring) !important;
  min-height: 42px !important;
}

#submit-btn:hover {
  filter: brightness(1.05);
}

#stop-btn {
  border-radius: var(--radius-sm) !important;
  background: #fff7ed !important;
  border: 1px solid #fed7aa !important;
  color: #9a3412 !important;
  font-weight: 600 !important;
  min-height: 42px !important;
}

#clear-btn {
  border-radius: var(--radius-sm) !important;
  background: var(--bg-muted) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-muted) !important;
  font-weight: 600 !important;
  min-height: 42px !important;
}

#new-chat-btn {
  border-radius: var(--radius-sm) !important;
  background: var(--success-soft) !important;
  border: 1px solid #a7f3d0 !important;
  color: var(--success) !important;
  font-weight: 600 !important;
  min-height: 42px !important;
}

#status-box textarea,
#status-box input {
  background: var(--bg-muted) !important;
  border: 1px dashed var(--border) !important;
  color: var(--text-muted) !important;
  font-size: 12px !important;
  border-radius: var(--radius-sm) !important;
}

#brand-panel {
  min-width: 220px !important;
  max-width: 260px !important;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 18px 16px;
  box-shadow: var(--shadow-sm);
}

.brand-logo-fallback {
  width: 100%;
  aspect-ratio: 1.2;
  border-radius: var(--radius-md);
  background: linear-gradient(145deg, #fff7ed, #ffedd5);
  border: 1px solid #fed7aa;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 42px;
  font-weight: 800;
  color: #ea580c;
}

#brand-panel .brand-name {
  margin-top: 14px;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  text-align: center;
}

#brand-panel .brand-sub {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.7;
  text-align: center;
}

.brand-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
  margin-top: 14px;
}

.brand-tag {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--bg-muted);
  color: var(--text-muted);
  border: 1px solid var(--border);
}

#action-trigger {
  display: none !important;
}

#action-trigger textarea {
  display: none !important;
}

@media (max-width: 1100px) {
  #brand-panel {
    display: none !important;
  }
}

'''

agent = XkChatAgent()
_is_processing = threading.Event()

PANEL_PRICE = """
<div class="panel">
  <div class="panel-title">星空算价助手</div>
  <p><b>使用方式</b>：选择本模式后，在右侧输入区发送即可。</p>
  <p>① <b>上传 Excel</b> — 表格内运单批量算价<br>
  ② <b>固定格式文本</b> — 识别为单条运单<br>
  ③ <b>系统截图</b> — 自动提取运单信息<br>
  ④ <b>不上传</b> — 使用《启恒客户追踪表》算价</p>
  <p>📐 <b>必填</b>：总体积、重量、件数。品名/类型/包装可留空（默认：日用品 / 日用品 / 箱）。</p>
</div>
"""

PANEL_ZT = """
<div class="panel">
  <div class="panel-title">中通算价助手</div>
  <p><b>使用方式</b>：选择本模式后点「发送」，约 1~2 分钟返回报价。</p>
  <p>支持 Excel、文本运单、截图识别，或直接使用现有追踪表 — 规则与星空算价一致。</p>
  <p style="color:#64748b;font-size:12px;">文本需包含「地址：」；截图地址不完整时会提示补全或上传 Excel。</p>
</div>
"""

PANEL_CONTACT = """
<div class="panel">
  <div class="panel-title">天津启恒物流有限公司</div>
  <p><b>业务范围</b><br>整车运输 / 零担配送 / 仓储管理 / 同城配送</p>
  <p><b>招商合作</b><br>欢迎承运商、司机、货主洽谈合作</p>
  <p><b>联系方式</b><br>
  启恒客服：胡女士 13302045636<br>
  地址：天津市北辰区大桂道刘房子产业园 J 座 12 号<br>
  邮箱：35730878@qq.com · 网址：www.qihey.cn</p>
</div>
"""

BRAND_HTML = """
<div class="brand-logo-fallback">启</div>
<div class="brand-name">天津启恒物流</div>
<div class="brand-sub">智能算价 · 高效履约<br>全国干线 · 仓配一体</div>
<div class="brand-tags">
  <span class="brand-tag">零担</span>
  <span class="brand-tag">整车</span>
  <span class="brand-tag">仓储</span>
  <span class="brand-tag">同城</span>
</div>
"""

WELCOME_MESSAGE = """**👋 您好，我是启恒物流智能算价助手**

我可以帮您快速完成运费测算，支持以下三种方式：

- **文字描述**：说明品名、数量、规格、尺寸、收货地址及联系人等
- **Excel 运单**：上传文件，自动识别并批量算价
- **图片截图**：上传微信沟通记录或系统截图，自动提取关键信息

> 提示：信息越完整，报价越准确。若缺少字段，我会主动向您确认。

**示例输入：**
货物名称：抽纸，件数：XXX箱，重量：XXXkg，尺寸：XXX×XXX×XXXmm，收货地址：河北省石家庄市桥西区中山西路123号，联系人：胡女士，电话：13302045636，送仓费：XXX元"""

CHATBOT_PLACEHOLDER = (
    "货物名称：抽纸，件数：XXX箱，重量：XXXkg，尺寸：XXX×XXX×XXXmm，"
    "收货地址：河北省石家庄市桥西区中山西路123号，联系人：胡女士，电话：13302045636，送仓费：XXX元"
)
INPUT_PLACEHOLDER = "粘贴运单信息，或告诉我品名、件数、重量、尺寸、地址、联系人和电话。"

NAV_ACTIVE = ["nav-btn", "nav-active"]
NAV_IDLE = ["nav-btn"]


def _nav_updates(active_index: int):
    return tuple(
        gr.update(elem_classes=NAV_ACTIVE if i == active_index else NAV_IDLE)
        for i in range(4)
    )


def extract_address(text):
    if not text:
        return None
    m = re.search(r"(?:收货)?地址[:：]\s*([^\n,，。;；]+)", text)
    if m:
        addr = m.group(1).strip()[:20]
        if addr:
            return addr
    m2 = re.search(r"([\u4e00-\u9fa5]{2,}(?:省|市|区|县)[\u4e00-\u9fa5]{0,15})", text)
    return m2.group(1)[:20] if m2 else None


def _extract_path(files):
    if not files:
        return None
    target = files[-1] if isinstance(files, list) else files
    if isinstance(target, dict):
        return target.get("path") or target.get("name")
    return str(target)


def _session_label(s):
    title = s.get("title")
    if title:
        return title
    return s["session_id"][:8]


def _zt_title_from_result(md):
    addrs = []
    for m in re.finditer(r"\|\s*\d+\s*\|\s*([^|]+?)\s*\|", md or ""):
        a = m.group(1).strip()
        if a and not a.startswith("¥") and a != "收货地址":
            addrs.append(a)
    if not addrs:
        return None
    first = addrs[0][:20]
    return f"{first} 等{len(addrs)}单" if len(addrs) > 1 else first


def render_history_panel(keyword=None):
    if keyword and keyword.strip():
        sessions = search_sessions(keyword)
    else:
        sessions = get_all_sessions()

    clearall_block = (
        '<div class="hist-clearall-row">'
        '<button class="hist-clearall-btn" onclick="showClearAll()">🗑 清空历史记录</button>'
        "</div>"
        '<div id="clearall-dialog" class="dialog-overlay"><div class="dialog-box">'
        '<div class="dialog-header">确认清空</div>'
        '<div class="dialog-body"><p>确认<b>清空所有历史对话记录</b>？</p>'
        '<p class="dialog-warning">此操作不可恢复，将删除全部会话（无法还原）。</p></div>'
        '<div class="dialog-footer"><button class="dialog-btn cancel" onclick="cancelClearAll()">取消</button>'
        '<button class="dialog-btn confirm danger" onclick="confirmClearAll()">确认清空</button></div></div></div>'
    )

    if not sessions:
        return (
            '<div class="panel hist-panel"><div class="panel-title">历史对话记录</div>'
            '<div class="hist-search-row"><input type="text" id="hist-search-input" class="hist-search-input" placeholder="输入地址、关键词搜索会话" />'
            '<button id="hist-search-btn" class="hist-search-btn" onclick="histSearch()">搜索</button></div>'
            '<p style="color:#94a3b8;text-align:center;padding:20px;">暂无历史记录。</p>'
            + clearall_block
            + "</div>"
        )

    def esc_js(s):
        return (
            s.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )

    items = ""
    for s in sessions[:50]:
        label = _session_label(s)
        sid = s["session_id"]
        meta = "{} 条 · {}".format(s["msg_count"], s["last_time"] or s["start_time"] or "")
        items += f'<div class="hist-item" data-sid="{sid}">'
        items += f'<span class="hist-main" onclick="switchSession(\'{sid}\')">'
        items += f"<b>{esc_js(label)}</b>"
        items += f'<span class="hist-meta">{esc_js(meta)}</span>'
        items += "</span>"
        items += '<button class="hist-more" onclick="event.stopPropagation(); toggleMenu(this)">&#x22EF;</button>'
        items += '<div class="hist-dropdown">'
        items += f'<a onclick="event.stopPropagation(); showRename(\'{sid}\',\'{esc_js(label)}\')">重命名</a>'
        items += f'<a class="danger" onclick="event.stopPropagation(); showDelete(\'{sid}\',\'{esc_js(label)}\')">删除</a>'
        items += "</div></div>"

    html = '<div class="panel hist-panel">'
    html += '<div class="panel-title">历史对话记录</div>'
    html += '<div class="hist-search-row"><input type="text" id="hist-search-input" class="hist-search-input" placeholder="输入地址、关键词搜索会话" />'
    html += '<button id="hist-search-btn" class="hist-search-btn" onclick="histSearch()">搜索</button></div>'
    html += f'<div id="hist-items">{items}</div>'
    html += clearall_block
    html += '<div id="rename-dialog" class="dialog-overlay"><div class="dialog-box">'
    html += '<div class="dialog-header">重命名会话</div>'
    html += '<div class="dialog-body"><input type="text" id="rename-input" class="dialog-input" placeholder="输入新的会话名称" /></div>'
    html += '<div class="dialog-footer"><button class="dialog-btn cancel" onclick="cancelRename()">取消</button>'
    html += '<button class="dialog-btn confirm" onclick="confirmRename()">确认</button></div></div></div>'
    html += '<div id="delete-dialog" class="dialog-overlay"><div class="dialog-box">'
    html += '<div class="dialog-header">确认删除</div>'
    html += '<div class="dialog-body"><p>确认删除「<span id="delete-session-name" class="dialog-highlight"></span>」？</p>'
    html += '<p class="dialog-warning">此操作不可恢复。</p></div>'
    html += '<div class="dialog-footer"><button class="dialog-btn cancel" onclick="cancelDelete()">取消</button>'
    html += '<button class="dialog-btn confirm danger" onclick="confirmDelete()">确认删除</button></div></div></div>'
    html += "</div>"
    return html


init_db()
_initial_session_id = str(uuid.uuid4())
_initial_history = load_history(_initial_session_id) or [{"role": "assistant", "content": WELCOME_MESSAGE}]

# --- JS bridge (history panel) ---
HIST_JS = r"""
document.addEventListener('click', function(e) {
  if (!e.target.closest('.hist-item')) {
    document.querySelectorAll('.hist-dropdown').forEach(function(d) { d.style.display = 'none'; });
  }
});
window.toggleMenu = function(btn) {
  document.querySelectorAll('.hist-dropdown').forEach(function(d) { d.style.display = 'none'; });
  var dropdown = btn.nextElementSibling;
  if (dropdown && dropdown.classList.contains('hist-dropdown')) {
    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
  }
};
window.switchSession = function(sid) { closeAllMenus(); triggerAction({action: 'view', sid: sid}); };
var currentRenameSid = null;
window.showRename = function(sid, name) {
  closeAllMenus(); currentRenameSid = sid;
  var input = document.getElementById('rename-input');
  if (input) { input.value = name; input.focus(); }
  var dialog = document.getElementById('rename-dialog');
  if (dialog) dialog.style.display = 'flex';
};
window.cancelRename = function() {
  currentRenameSid = null;
  var dialog = document.getElementById('rename-dialog');
  if (dialog) dialog.style.display = 'none';
};
window.confirmRename = function() {
  var input = document.getElementById('rename-input');
  var newName = input ? input.value.trim() : '';
  if (newName && currentRenameSid) { triggerAction({action: 'rename', sid: currentRenameSid, name: newName}); }
  cancelRename();
};
var currentDeleteSid = null;
window.showDelete = function(sid, name) {
  closeAllMenus(); currentDeleteSid = sid;
  var nameSpan = document.getElementById('delete-session-name');
  if (nameSpan) nameSpan.textContent = name;
  var dialog = document.getElementById('delete-dialog');
  if (dialog) dialog.style.display = 'flex';
};
window.cancelDelete = function() {
  currentDeleteSid = null;
  var dialog = document.getElementById('delete-dialog');
  if (dialog) dialog.style.display = 'none';
};
window.confirmDelete = function() {
  if (currentDeleteSid) { triggerAction({action: 'delete', sid: currentDeleteSid}); }
  cancelDelete();
};
window.showClearAll = function() {
  closeAllMenus();
  var dialog = document.getElementById('clearall-dialog');
  if (dialog) dialog.style.display = 'flex';
};
window.cancelClearAll = function() {
  var dialog = document.getElementById('clearall-dialog');
  if (dialog) dialog.style.display = 'none';
};
window.confirmClearAll = function() { triggerAction({action: 'clearAll'}); cancelClearAll(); };
window.histSearch = function() {
  var input = document.getElementById('hist-search-input');
  var kw = input ? input.value.trim() : '';
  triggerAction({action: 'search', keyword: kw});
};
function closeAllMenus() {
  document.querySelectorAll('.hist-dropdown').forEach(function(d) { d.style.display = 'none'; });
}
function triggerAction(obj) {
  var container = document.getElementById('action-trigger');
  if (!container) {
    var fallback = document.createElement('input');
    fallback.type = 'hidden';
    fallback.id = 'action-trigger';
    document.body.appendChild(fallback);
    container = fallback;
  }
  var input = container.querySelector ? container.querySelector('textarea') : null;
  if (!input) {
    if (container.tagName === 'INPUT') input = container;
    else if (container.querySelector) input = container.querySelector('textarea');
  }
  if (!input) return;
  input.value = JSON.stringify(obj);
  input.dispatchEvent(new Event('input', {bubbles: true}));
  setTimeout(function() { input.dispatchEvent(new Event('change', {bubbles: true})); }, 50);
}
window.triggerAction = triggerAction;
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') { cancelRename(); cancelDelete(); cancelClearAll(); }
  if (e.key === 'Enter' && e.target.id === 'hist-search-input') { e.preventDefault(); histSearch(); }
  if (e.key === 'Enter' && e.target.id === 'rename-input') { e.preventDefault(); confirmRename(); }
});
document.addEventListener('click', function(e) {
  if (e.target.id === 'rename-dialog') cancelRename();
  if (e.target.id === 'delete-dialog') cancelDelete();
  if (e.target.id === 'clearall-dialog') cancelClearAll();
});
"""

def bot_respond(message, history, files, image_files, session_id, current_mode):
    """Gradio 聊天回调：中通算价走专用链路，其余走星空智能体。"""
    if _is_processing.is_set():
        history = history or []
        history.append({"role": "assistant", "content": "⏸ 当前请求正在处理中，请稍等..."})
        yield history
        return

    _is_processing.set()
    try:
        user_msg = message.get("text", "") if isinstance(message, dict) else str(message)
        actual_file_path = _extract_path(files)
        actual_image_path = _extract_path(image_files)

        if current_mode == "zt" or "中通" in user_msg:
            history = history or []
            text_order = parse_text_order(user_msg) if (_ZT_OK and user_msg.strip()) else None
            force_addr = "强制" in user_msg

            user_text = user_msg.strip() or "🚚 中通算价"
            if actual_file_path:
                user_text += f"（使用上传的运单：{os.path.basename(actual_file_path)}）"
            elif text_order:
                user_text += "（解析为一条新运单）"
            elif actual_image_path:
                user_text += f"（识别截图：{os.path.basename(actual_image_path)}）"
            else:
                user_text += "（使用现有《启恒客户追踪表.xlsx》）"
            history.append({"role": "user", "content": user_text})

            if not _ZT_OK:
                history.append(
                    {
                        "role": "assistant",
                        "content": "❌ 中通算价模块未加载成功，请检查 zt_bridge.py 与 zt_input.py 是否放在 xkagent 目录下。",
                    }
                )
                yield history
                return

            def _wait(msg):
                history.append({"role": "assistant", "content": msg})

            if actual_file_path:
                _wait("⏳ 正在连接中通系统实时报价，逐单填写并抓取最低价方案，通常需要 1~2 分钟，请勿关闭页面或重复点击…")
                yield history
                result = run_zt_pricing(actual_file_path)
            elif text_order:
                missing = find_missing_required(text_order)
                if missing:
                    result = (
                        "⚠️ 文本运单缺少**必填字段：" + "、".join(missing) + "**，无法算价。\n\n"
                        "「总体积 / 重量 / 件数」为必填项；"
                        "物品名称、物品类型、包装类型可以不填（会自动填默认值：日用品 / 箱）。\n\n"
                        "**请按以下格式补全后重新发送**：\n\n"
                        "> 货物名称：抽纸，件数：20箱，重量：200kg，尺寸：550×380×320mm，"
                        "收货地址：河北省石家庄市桥西区中山西路123号，联系人：胡女士，电话：13312345678，送仓费：100"
                    )
                else:
                    err = write_orders_to_excel([text_order], ZT_EXCEL)
                    if err:
                        result = "⚠️ " + err
                    else:
                        _wait(
                            "✅ 已解析文本运单并写入追踪表：\n\n"
                            + order_markdown(text_order)
                            + "\n\n⏳ 正在连接中通系统实时报价，通常需要 1~2 分钟…"
                        )
                        yield history
                        result = run_zt_pricing(None)
            elif actual_image_path:
                _wait("⏳ 正在识别截图中的运单信息…")
                yield history
                orders, raw = extract_orders_via_vision(actual_image_path)
                if not orders:
                    result = (
                        "⚠️ 未能从截图中识别出任何含「详细地址」的运单，无法算价。\n\n"
                        "**识别原文**：\n\n" + (raw[:1200] or "（空）") + "\n\n**本次识别配置**：\n\n`" + vision_config_summary() + "`"
                    )
                else:
                    trunc = [i + 1 for i, o in enumerate(orders) if address_looks_incomplete(o.get("详细地址"))]
                    if trunc and not force_addr:
                        detail = "\n".join(f"- 第 {i} 单：{o.get('详细地址') or '（空）'}" for i, o in enumerate(orders, 1))
                        result = (
                            "⚠️ **识别到的「详细地址」疑似不完整，已暂停算价**（避免报价不准）。\n\n"
                            f"涉及运单：第 {'、'.join(map(str, trunc))} 单\n\n"
                            "**本次识别到的地址**：\n\n" + detail + "\n\n"
                            "若确认地址够用：消息中带「**强制**」再发一次。"
                        )
                    else:
                        bad = [(idx + 1, find_missing_required(o)) for idx, o in enumerate(orders)]
                        bad = [(idx, m) for idx, m in bad if m]
                        if bad:
                            lines = [f"- 第 {idx} 张运单缺少必填字段：{'、'.join(m)}" for idx, m in bad]
                            result = "⚠️ 以下运单识别结果缺少**必填字段（总体积/重量/件数）**：\n\n" + "\n".join(lines)
                        else:
                            err = write_orders_to_excel(orders, ZT_EXCEL)
                            if err:
                                result = "⚠️ " + err
                            else:
                                preview = "\n\n".join(order_markdown(o) for o in orders)
                                _wait(
                                    f"✅ 已从截图识别 {len(orders)} 张运单并写入追踪表：\n\n"
                                    + preview
                                    + "\n\n⏳ 正在连接中通系统实时报价，通常需要 1~2 分钟…"
                                )
                                yield history
                                result = run_zt_pricing(None)
            else:
                _wait("⏳ 正在连接中通系统实时报价，逐单填写并抓取最低价方案，通常需要 1~2 分钟…")
                yield history
                result = run_zt_pricing(None)

            history[-1] = {"role": "assistant", "content": result}
            save_messages(
                session_id,
                [{"role": "user", "content": user_text}, {"role": "assistant", "content": result}],
            )
            try:
                _zt_title = _zt_title_from_result(result)
                if _zt_title:
                    set_session_title(session_id, _zt_title)
            except Exception as _te:
                print(f"[会话命名] 设置标题失败：{_te}")
            yield history
            return

        reply, out_file = agent.chat(user_msg, file_path=actual_file_path, image_path=actual_image_path)
        history = history or []
        history.append({"role": "user", "content": user_msg})
        assistant_content = reply + ("\n\n📎 " + str(out_file) if out_file else "")
        history.append({"role": "assistant", "content": assistant_content})
        save_messages(
            session_id,
            [{"role": "user", "content": user_msg}, {"role": "assistant", "content": assistant_content}],
        )
        addr = extract_address(user_msg)
        if addr:
            set_session_title(session_id, addr)
        yield history
    finally:
        _is_processing.clear()


def handle_action(action_data):
    try:
        data = json.loads(action_data)
    except Exception:
        return gr.update(), gr.update(), gr.update()

    action = data.get("action")
    sid = data.get("sid")
    name = data.get("name")
    keyword = data.get("keyword")

    if action == "view":
        history = load_history(sid) or [{"role": "assistant", "content": WELCOME_MESSAGE}]
        return gr.update(value=sid), gr.update(value=history), gr.update(value=render_history_panel())

    if action == "rename":
        if sid and name and name.strip():
            rename_session(sid, name.strip())
        return gr.update(), gr.update(), gr.update(value=render_history_panel())

    if action == "delete":
        if sid:
            clear_history(sid)
        history = [{"role": "assistant", "content": WELCOME_MESSAGE}]
        return gr.update(value=_initial_session_id), gr.update(value=history), gr.update(value=render_history_panel())

    if action == "search":
        kw = keyword.strip() if keyword and keyword.strip() else None
        return gr.update(), gr.update(), gr.update(value=render_history_panel(kw))

    if action == "clearAll":
        try:
            delete_all_sessions()
        except Exception as _ce:
            print(f"[清空历史] 失败：{_ce}")
        new_sid = str(uuid.uuid4())
        history = [{"role": "assistant", "content": WELCOME_MESSAGE}]
        return gr.update(value=new_sid), gr.update(value=history), gr.update(value=render_history_panel())

    return gr.update(), gr.update(), gr.update()


theme = gr.themes.Soft(
    primary_hue="orange",
    secondary_hue="slate",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Noto Sans SC"), "system-ui", "sans-serif"],
).set(body_background_fill="transparent", block_background_fill="white", block_border_width="0px")

with gr.Blocks(fill_height=True) as demo:
    current_session_id = gr.State(_initial_session_id)
    current_mode = gr.State("agent")

    with gr.Row(elem_id="title-bar", equal_height=True):
        gr.HTML(
            """
            <div class="title-main">
              <h1>启恒物流 · 智能算价助手</h1>
              <p class="title-sub">Excel / 文本 / 截图多通道报价 · 会话自动保存</p>
            </div>
            """
        )
        gr.HTML('<span class="title-badge">● 在线服务</span>')

    with gr.Row(elem_classes=["app-shell"]):
        with gr.Column(scale=1, elem_id="side-nav"):
            gr.HTML(
                """
                <div class="side-nav-head">
                  <div class="sn-title">功能导航</div>
                  <div class="sn-sub">选择算价通道与历史记录</div>
                </div>
                """
            )
            with gr.Row(elem_id="nav-btns"):
                btn_price = gr.Button("💬 星空算价", elem_classes=NAV_ACTIVE)
                btn_zt = gr.Button("🚚 中通算价", elem_classes=NAV_IDLE)
                btn_history = gr.Button("📋 历史对话", elem_classes=NAV_IDLE)
                btn_contact = gr.Button("🏢 招商与联系", elem_classes=NAV_IDLE)
            with gr.Column(elem_id="side-panel-wrap"):
                side_content = gr.HTML(PANEL_PRICE)

        with gr.Column(scale=6, elem_id="chat-panel"):
            with gr.Column(elem_id="answer-area"):
                gr.HTML('<div class="section-label">对话 / 回答</div>')
                chatbot = gr.Chatbot(height=580, value=_initial_history, placeholder=CHATBOT_PLACEHOLDER)

            with gr.Column(elem_id="input-area"):
                gr.HTML('<div class="section-label">输入运单</div>')
                msg_input = gr.Textbox(placeholder=INPUT_PLACEHOLDER, show_label=False, lines=3)
                with gr.Row(elem_classes=["upload-row"]):
                    file_upload = gr.File(label="Excel 运单", file_types=[".xlsx", ".xls"], scale=1)
                    image_upload = gr.File(
                        label="截图 / 图片", file_types=[".png", ".jpg", ".jpeg", ".bmp", ".webp"], scale=1
                    )
                with gr.Row(elem_id="action-row"):
                    new_chat_btn = gr.Button("➕ 新建对话", elem_id="new-chat-btn", scale=1)
                    submit_btn = gr.Button("发送", variant="primary", elem_id="submit-btn", scale=2)
                    stop_btn = gr.Button("暂停", elem_id="stop-btn", scale=1)
                    clear_btn = gr.Button("清空对话", elem_id="clear-btn", scale=1)
                status = gr.Textbox(label="", show_label=False, interactive=False, elem_id="status-box", value="当前模式：星空智能算价")

        with gr.Column(scale=1, elem_id="brand-panel"):
            if os.path.exists(LOGO_PATH):
                gr.Image(value=LOGO_PATH, show_label=False, container=False, height=160)
            else:
                gr.HTML(BRAND_HTML)

    action_trigger = gr.Textbox(elem_id="action-trigger")
    try:
        gr.HTML("", js=HIST_JS)  # Gradio 4.40+
    except TypeError:
        gr.HTML("", js_on_load=HIST_JS)  # 旧版 Gradio

    nav_outputs = [current_mode, side_content, status, btn_price, btn_zt, btn_history, btn_contact]

    def on_nav_price():
        return ("agent", PANEL_PRICE, "当前模式：星空智能算价 —— 点「发送」开始对话", *_nav_updates(0))

    def on_nav_zt():
        return ("zt", PANEL_ZT, "当前模式：中通算价 —— 上传 Excel（可选）后点「发送」，约需 1~2 分钟", *_nav_updates(1))

    def on_nav_history():
        return ("agent", render_history_panel(), "已打开历史对话列表", *_nav_updates(2))

    def on_nav_contact():
        return ("agent", PANEL_CONTACT, "招商与联系", *_nav_updates(3))

    btn_price.click(fn=on_nav_price, outputs=nav_outputs)
    btn_zt.click(fn=on_nav_zt, outputs=nav_outputs)
    btn_history.click(fn=on_nav_history, outputs=nav_outputs)
    btn_contact.click(fn=on_nav_contact, outputs=nav_outputs)

    submit_btn.click(
        fn=bot_respond,
        inputs=[msg_input, chatbot, file_upload, image_upload, current_session_id, current_mode],
        outputs=[chatbot],
    ).then(fn=lambda: ("", None, None), outputs=[msg_input, file_upload, image_upload])

    msg_input.submit(
        fn=bot_respond,
        inputs=[msg_input, chatbot, file_upload, image_upload, current_session_id, current_mode],
        outputs=[chatbot],
    ).then(fn=lambda: ("", None, None), outputs=[msg_input, file_upload, image_upload])

    stop_btn.click(fn=lambda: (_is_processing.clear(), "已暂停，可重新输入"), outputs=[status]).then(
        fn=lambda: ("", None, None), outputs=[msg_input, file_upload, image_upload]
    )

    def on_clear(session_id):
        clear_history(session_id)
        return (
            [{"role": "assistant", "content": WELCOME_MESSAGE}],
            "",
            None,
            None,
            "已清空当前对话",
            "agent",
            *_nav_updates(0),
        )

    clear_btn.click(
        fn=on_clear,
        inputs=[current_session_id],
        outputs=[chatbot, msg_input, file_upload, image_upload, status, current_mode, *nav_outputs[3:]],
    )

    def on_new_chat():
        new_sid = str(uuid.uuid4())
        return (
            new_sid,
            [{"role": "assistant", "content": WELCOME_MESSAGE}],
            "",
            None,
            None,
            render_history_panel(),
            "agent",
            *_nav_updates(0),
        )

    new_chat_btn.click(
        fn=on_new_chat,
        outputs=[current_session_id, chatbot, msg_input, file_upload, image_upload, side_content, current_mode, *nav_outputs[3:]],
    )

    action_trigger.change(fn=handle_action, inputs=[action_trigger], outputs=[current_session_id, chatbot, side_content])
    demo.load(fn=lambda: PANEL_PRICE, outputs=[side_content])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=theme, css=CSS)
