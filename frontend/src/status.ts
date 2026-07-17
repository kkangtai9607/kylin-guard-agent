const states: Record<string, string> = {
  READ_ONLY: "运维模式",
  DEMO: "演示模式",
  CONTROLLED_EXECUTION: "运维模式",
  ONLINE: "运行正常",
  SUCCEEDED: "已完成",
  FAILED: "失败",
  BLOCKED: "已阻断",
  CANCELLED: "已取消",
  ROLLED_BACK: "已回滚",
  PENDING: "待确认",
  APPROVED: "已确认",
  CONSUMED: "已执行",
  REJECTED: "已拒绝",
  OPEN: "待处理",
  ACKNOWLEDGED: "已确认",
  RESOLVED: "已解决",
  CLOSED: "已关闭",
  WARNING: "警告",
  CRITICAL: "严重",
  INFO: "提示",
  ELIGIBLE: "可处理",
};

export function zhStatus(value: unknown): string {
  return states[String(value)] || String(value ?? "—");
}
