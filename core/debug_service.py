# core/services/debug_service.py
# 除虫机制：定期扫描知识库，发现失效/可疑条目并写入质量保障表
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from ..db import db_cursor
from .. import safety_scan
from core.services import quality_service


def scan_knowledge_base_sample(limit: int = 20) -> Dict[str, Any]:
    """
    抽样扫描知识库中最近入库的条目，重新进行安全扫描和语法验证。
    发现异常则写入 quality_issues。
    返回扫描报告。
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, task, solution, verified, created_at
            FROM knowledge_base
            WHERE verified = 1
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()

    total_scanned = 0
    issues_created = 0

    for row in rows:
        row = dict(row)
        total_scanned += 1
        solution = row.get("solution") or ""

        # 1. 安全扫描
        risk = safety_scan.analyze_risk(solution)
        if risk["level"] == "high":
            quality_service.submit_debug_issue(
                title=f"知识库 #{row['id']} 存在高风险内容",
                detail=risk["message"] + f"\n任务: {row['task'][:100]}",
                severity=quality_service.SEVERITY_HIGH,
                source_id=str(row["id"])
            )
            issues_created += 1
            continue

        # 2. 基本完整性检查（方案为空或过短）
        if len(solution.strip()) < 10:
            quality_service.submit_debug_issue(
                title=f"知识库 #{row['id']} 方案内容过短或为空",
                detail=f"任务: {row['task'][:100]}\n方案长度: {len(solution)}",
                severity=quality_service.SEVERITY_LOW,
                source_id=str(row["id"])
            )
            issues_created += 1

    return {
        "total_scanned": total_scanned,
        "issues_created": issues_created,
        "scanned_at": datetime.now().isoformat()
    }


def scan_all_knowledge_base(batch_size: int = 50) -> Dict[str, Any]:
    """
    分批扫描整个知识库。适合在黑夜/日食等特殊状态下调用。
    """
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM knowledge_base WHERE verified = 1")
        total = cur.fetchone()["cnt"]

    scanned_total = 0
    issues_total = 0
    offset = 0

    while offset < total:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, task, solution FROM knowledge_base
                WHERE verified = 1
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, (batch_size, offset))
            rows = cur.fetchall()

        if not rows:
            break

        for row in rows:
            row = dict(row)
            scanned_total += 1
            solution = row.get("solution") or ""
            risk = safety_scan.analyze_risk(solution)
            if risk["level"] == "high":
                quality_service.submit_debug_issue(
                    title=f"知识库 #{row['id']} 存在高风险内容",
                    detail=risk["message"] + f"\n任务: {row['task'][:100]}",
                    severity=quality_service.SEVERITY_HIGH,
                    source_id=str(row["id"])
                )
                issues_total += 1
            elif len(solution.strip()) < 10:
                quality_service.submit_debug_issue(
                    title=f"知识库 #{row['id']} 方案内容过短或为空",
                    detail=f"任务: {row['task'][:100]}\n方案长度: {len(solution)}",
                    severity=quality_service.SEVERITY_LOW,
                    source_id=str(row["id"])
                )
                issues_total += 1

        offset += len(rows)

    return {
        "total_scanned": scanned_total,
        "issues_created": issues_total,
        "scanned_at": datetime.now().isoformat()
    }


async def periodic_debug_scan(interval_hours: int = 6, sample_limit: int = 20):
    """
    后台定时任务：每 N 小时扫描一次知识库最近条目。
    """
    while True:
        try:
            report = await asyncio.to_thread(scan_knowledge_base_sample, sample_limit)
            print(f"[除虫机制] 扫描完成: 共 {report['total_scanned']} 条，发现 {report['issues_created']} 个问题")
        except Exception as e:
            print(f"[除虫机制] 扫描异常: {e}")

        await asyncio.sleep(interval_hours * 3600)
