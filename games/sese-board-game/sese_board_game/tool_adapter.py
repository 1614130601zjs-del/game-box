from __future__ import annotations
import os
from pathlib import Path
from typing import Any

from .engine import GAME_ID, run_command


TOOL_NAME = GAME_ID


AI_CONTEXT_INSTRUCTION = (
    "剧情生成规则：本工具只负责棋盘、骰子、位置、事件、选项和游戏状态，不直接读取客户端私有数据。"
    "调用本工具后生成剧情时，必须优先读取并遵循当前 AI 客户端已经提供的有效上下文，包括角色人设/角色卡、世界书、作者注释、当前对话历史以及其他已注入的设定。"
    "如果客户端提供了这些上下文，应以它们作为人物性格、关系、世界观和剧情连续性的依据；不得自行臆造与现有设定冲突的人物信息。"
    "不要要求用户把已经在当前上下文中的人设或世界书再次粘贴给 MCP。"
)


def default_save_path() -> Path:
    return Path(os.environ.get("SESE_BOARD_GAME_SAVE", ".sese_board_game.json"))


def get_tools_for_inject() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": (
                    "执行涩涩走格棋的一步命令，并返回棋盘、公开状态、待处理事件和玩家可读文本。"
                    "可用命令：status、new_game、roll、roll 3、submit <内容>、approve [反馈]、reject [理由]、choose <选项id>、pass、end_game。"
                    + AI_CONTEXT_INSTRUCTION
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "游戏命令，例如：status、roll、submit <内容>、approve 做得不错、choose add_prop、pass、new_game。",
                        },
                        "save_path": {
                            "type": "string",
                            "description": "可选 JSON 存档路径。默认使用 SESE_BOARD_GAME_SAVE 或当前目录下的 .sese_board_game.json。",
                        },
                    },
                    "required": ["command"],
                },
            },
        }
    ]


def execute_tool(arguments: dict[str, Any] | None = None) -> str:
    args = arguments if isinstance(arguments, dict) else {}
    command = str(args.get("command") or "status")
    save_path = args.get("save_path") or default_save_path()
    payload = run_command(command, save_path=save_path)
    return str(payload.get("ai_text") or payload.get("text") or "").strip()
