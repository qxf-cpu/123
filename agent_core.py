"""Stub agent for UI preview — replace with your real XkChatAgent in production."""


class XkChatAgent:
    def chat(self, user_msg, file_path=None, image_path=None):
        parts = ["这是预览环境的占位回复。接入 `XkChatAgent` 后将走真实算价逻辑。"]
        if file_path:
            parts.append(f"已收到 Excel：`{file_path}`")
        if image_path:
            parts.append(f"已收到图片：`{image_path}`")
        if user_msg.strip():
            parts.append(f"您说：{user_msg.strip()[:200]}")
        return "\n\n".join(parts), None
