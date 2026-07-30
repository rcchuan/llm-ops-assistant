# -*- coding: utf-8 -*-
"""
Flask 后端：供 index.html 调用 Dify 答疑 API（Key 仅存服务端 .env）

启动:
    python app.py
访问:
    http://127.0.0.1:5000/
"""

from __future__ import annotations

import traceback
import uuid

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import config
from dify_api import chat_and_log, list_recent_logs

app = Flask(__name__, static_folder="static")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "dify_configured": bool(config.DIFY_APP_API_KEY)})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    前端自测接口：接收运维问题，返回 AI 答疑。
    Body JSON: { "question": "...", "user_id": "可选" }
    """
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "问题不能为空"}), 400

    user_id = data.get("user_id") or f"web-{uuid.uuid4().hex[:8]}"
    try:
        result = chat_and_log(question, user_id=user_id)
        return jsonify(
            {
                "answer": result.get("answer", ""),
                "conversation_id": result.get("conversation_id", ""),
                "message_id": result.get("message_id", ""),
                "retriever_resources": result.get("metadata", {}).get("retriever_resources", []),
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc), "detail": traceback.format_exc()}), 500


@app.route("/api/logs", methods=["GET"])
def api_logs():
    limit = request.args.get("limit", 10, type=int)
    return jsonify({"logs": list_recent_logs(limit=limit)})


def main():
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)


if __name__ == "__main__":
    main()
