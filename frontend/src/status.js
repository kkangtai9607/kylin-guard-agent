const states = {
    READ_ONLY: "只读模式",
    DEMO: "演示模式",
    CONTROLLED_EXECUTION: "受控执行",
    ONLINE: "运行正常",
    SUCCEEDED: "已成功",
    FAILED: "失败",
    BLOCKED: "已阻断",
    PENDING: "待处理",
    APPROVED: "已批准",
    REJECTED: "已拒绝",
    OPEN: "待处理",
    ACKNOWLEDGED: "已确认",
    RESOLVED: "已解决",
    CLOSED: "已关闭",
    WARNING: "警告",
    CRITICAL: "严重",
    INFO: "提示",
};
export function zhStatus(value) {
    return states[String(value)] || String(value ?? "—");
}
