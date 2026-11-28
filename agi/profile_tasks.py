"""Reusable task templates for account-profile edits.

These are SASES browser action sequences, not direct API calls. The caller can
submit them through the normal local runtime approval path.
"""
from __future__ import annotations


def bilibili_signature_steps(text: str) -> list[dict]:
    return [
        {"tool": "browser.open", "args": {
            "url": "https://account.bilibili.com/account/home",
            "wait_ms": 6000,
        }},
        {"tool": "browser.click_target", "args": {
            "target": {"selector": "#ser-ul span:has-text(\"我的信息\")"},
            "wait_ms": 1500,
        }},
        {"tool": "browser.fill_targets", "args": {
            "targets": [{"target": {"selector": "textarea"}, "value": text}],
        }},
        {"tool": "browser.click_target", "args": {
            "target": {"role": "button", "name": "保存"},
        }},
        {"tool": "browser.snapshot", "args": {}},
    ]


def youtube_profile_steps(description: str, link_title: str, link_url: str) -> list[dict]:
    return [
        {"tool": "browser.open", "args": {
            "url": "https://studio.youtube.com/channel/UCBpL3hK22rzoNP70J8evpHQ/editing/profile",
            "wait_ms": 8000,
        }},
        {"tool": "browser.fill_targets", "args": {
            "targets": [{
                "target": {"selector": 'div[contenteditable="true"][aria-label*="介绍"]'},
                "value": description,
            }],
        }},
        {"tool": "browser.click_target", "args": {
            "target": {"role": "button", "name": "添加链接"},
        }},
        {"tool": "browser.fill_targets", "args": {
            "targets": [
                {"target": {"placeholder": "输入标题"}, "value": link_title},
                {"target": {"placeholder": "输入网址"}, "value": link_url},
            ],
        }},
        {"tool": "browser.click_target", "args": {
            "target": {"role": "button", "name": "发布"},
        }},
        {"tool": "browser.snapshot", "args": {}},
    ]
