from __future__ import annotations

import uuid
from typing import Any

from backend.app.agent.evidence import Evidence, EvidenceType
from backend.app.agent.runners import EvidenceRecord


class EvidenceNormalizer:
    """Convert untrusted Tool envelopes into bounded, typed RCA evidence."""

    def normalize(self, records: list[EvidenceRecord]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for record in records:
            data = record.payload.get("data")
            if not isinstance(data, dict):
                continue
            handler = getattr(self, f"_{record.tool_name}", None)
            if handler is not None:
                evidence.extend(handler(data))
            else:
                evidence.append(
                    self._item(
                        EvidenceType.METRIC,
                        record.tool_name,
                        f"{record.tool_name} evidence",
                        "collected",
                        0.1,
                        [record.tool_name],
                    )
                )
        return evidence[:200]

    def _system_snapshot(self, data: dict[str, Any]) -> list[Evidence]:
        items: list[Evidence] = []
        disk = data.get("disk")
        if isinstance(disk, dict):
            total = self._number(disk.get("total"))
            used = self._number(disk.get("used"))
            if total > 0:
                percent = used / total * 100
                items.append(
                    self._item(
                        EvidenceType.METRIC,
                        "system_snapshot",
                        "disk space usage",
                        round(percent, 2),
                        self._ratio_score(percent, 70, 95),
                        ["disk", "space"],
                    )
                )
        load = data.get("load_average")
        cpu_count = self._number(data.get("cpu_count"))
        if isinstance(load, list) and load and cpu_count > 0:
            ratio = self._number(load[0]) / cpu_count * 100
            items.append(
                self._item(
                    EvidenceType.METRIC,
                    "system_snapshot",
                    "cpu load",
                    round(ratio, 2),
                    self._ratio_score(ratio, 60, 150),
                    ["cpu", "load"],
                )
            )
        return items

    def _disk_usage_scan(self, data: dict[str, Any]) -> list[Evidence]:
        total = self._number(data.get("total"))
        used = self._number(data.get("used"))
        percent = used / total * 100 if total > 0 else 0
        return [
            self._item(
                EvidenceType.METRIC,
                "disk_usage_scan",
                "disk space",
                round(percent, 2),
                self._ratio_score(percent, 70, 95),
                ["disk", "space"],
            )
        ]

    def _large_file_scan(self, data: dict[str, Any]) -> list[Evidence]:
        files = data.get("files")
        if not isinstance(files, list):
            return []
        return [
            self._item(
                EvidenceType.LOG,
                "large_file_scan",
                "large file",
                str(item.get("path", "")),
                min(1.0, self._number(item.get("size")) / 1_000_000_000),
                ["disk", "space", "large_file"],
            )
            for item in files[:100]
            if isinstance(item, dict)
        ]

    def _zombie_process_scan(self, data: dict[str, Any]) -> list[Evidence]:
        zombies = data.get("zombies")
        count = len(zombies) if isinstance(zombies, list) else 0
        return [
            self._item(
                EvidenceType.PROCESS,
                "zombie_process_scan",
                "zombie process",
                count,
                min(1.0, count / 5),
                ["zombie", "process"],
            )
        ]

    def _process_list(self, data: dict[str, Any]) -> list[Evidence]:
        processes = data.get("processes")
        count = len(processes) if isinstance(processes, list) else 0
        return [
            self._item(
                EvidenceType.PROCESS,
                "process_list",
                "process inventory",
                count,
                0.1,
                ["process"],
            )
        ]

    def _service_status(self, data: dict[str, Any]) -> list[Evidence]:
        properties = data.get("properties")
        active = properties.get("ActiveState") if isinstance(properties, dict) else None
        failed = active not in {"active", None}
        return [
            self._item(
                EvidenceType.SERVICE,
                "service_status",
                "service status",
                str(active or "unknown"),
                0.9 if failed else 0.1,
                ["service", "failed"] if failed else ["service"],
            )
        ]

    def _journal_query(self, data: dict[str, Any]) -> list[Evidence]:
        lines = data.get("lines")
        count = len(lines) if isinstance(lines, list) else 0
        return [
            self._item(
                EvidenceType.LOG,
                "journal_query",
                "journal evidence",
                count,
                min(1.0, count / 100),
                ["journal", "service"],
            )
        ]

    @staticmethod
    def _item(
        evidence_type: EvidenceType,
        source: str,
        title: str,
        value: float | str | bool,
        anomaly: float,
        tags: list[str],
    ) -> Evidence:
        return Evidence(
            evidence_id=str(uuid.uuid4()),
            evidence_type=evidence_type,
            source=source,
            title=title,
            value=value,
            anomaly_score=max(0.0, min(1.0, anomaly)),
            temporal_score=0.8,
            trust_label="UNTRUSTED_DATA",
            tags=tags,
        )

    @staticmethod
    def _number(value: object) -> float:
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0

    @staticmethod
    def _ratio_score(value: float, warning: float, critical: float) -> float:
        if value <= warning:
            return max(0.0, value / warning * 0.3)
        return min(1.0, 0.3 + (value - warning) / (critical - warning) * 0.7)
