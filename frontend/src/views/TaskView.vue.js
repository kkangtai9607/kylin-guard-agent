import { computed, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";
import { useSession } from "../stores/session";
import { zhStatus } from "../status";
const session = useSession();
const examples = [
    "分析磁盘空间不足的原因，并列出安全清理候选",
    "查询网络状态",
    "检查 nginx 服务为什么异常",
    "ssh 服务有没有开启",
    "查看 CPU 占用和可疑进程",
    "检查 8080 端口由哪个进程占用",
];
const goal = ref("");
const task = ref();
const result = ref();
const approvals = ref([]);
const error = ref("");
const loading = ref(false);
const detailVisible = ref(false);
const detailTitle = ref("");
const detailJson = ref("");
const selectedCandidateIds = ref([]);
const executionSummaries = ref([]);
const eligibleCleanupDecisions = computed(() => (result.value?.cleanup_analysis || []).filter(canSelectCleanup));
const selectedCleanupDecisions = computed(() => {
    const selected = new Set(selectedCandidateIds.value);
    return eligibleCleanupDecisions.value.filter((item) => {
        const candidateId = item.candidate?.candidate_id;
        return Boolean(candidateId && selected.has(candidateId));
    });
});
const selectedCleanupBytes = computed(() => selectedCleanupDecisions.value.reduce((total, item) => total + (item.candidate?.size_bytes || 0), 0));
async function run() {
    if (!goal.value.trim())
        return;
    loading.value = true;
    error.value = "";
    approvals.value = [];
    selectedCandidateIds.value = [];
    executionSummaries.value = [];
    try {
        task.value = await api("/tasks", { method: "POST", body: JSON.stringify({ goal: goal.value.trim() }) });
        result.value = await api(`/tasks/${task.value.id}/run`, { method: "POST" });
        await loadApprovals();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "任务执行失败";
    }
    finally {
        loading.value = false;
    }
}
async function requestCleanup(candidate) {
    if (!task.value || !candidate?.candidate_id)
        return;
    const ok = await requestCleanupApproval(candidate);
    if (!ok)
        return;
    await loadApprovals();
    const approval = approvals.value.find((item) => item.status === "PENDING" && item.arguments_summary.candidate_id === candidate.candidate_id);
    if (!approval) {
        ElMessage.warning("清理确认已创建，请在本任务风险确认区域执行");
        return;
    }
    await confirmAndExecute(approval);
}
async function requestSelectedCleanup(candidates = selectedCleanupDecisions.value.map((item) => item.candidate).filter((item) => Boolean(item?.candidate_id))) {
    if (!task.value || !candidates.length)
        return;
    let created = 0;
    const failures = [];
    for (const candidate of candidates) {
        if (!candidate.candidate_id)
            continue;
        const ok = await requestCleanupApproval(candidate);
        if (ok) {
            created += 1;
        }
        else {
            failures.push(candidate.path);
        }
    }
    if (created) {
        ElMessage.success(`已创建 ${created} 个清理确认，请确认后执行`);
        selectedCandidateIds.value = selectedCandidateIds.value.filter((id) => !candidates.some((item) => item.candidate_id === id));
        await loadApprovals();
    }
    if (failures.length) {
        error.value = `部分候选创建失败：${failures.slice(0, 3).join("；")}${failures.length > 3 ? " 等" : ""}`;
    }
}
async function requestCleanupApproval(candidate) {
    if (!task.value || !candidate.candidate_id)
        return false;
    const argumentsValue = { candidate_id: candidate.candidate_id };
    try {
        await api("/executions/dry-run", { method: "POST", body: JSON.stringify({ tool_name: "safe_log_cleanup", arguments: argumentsValue }) });
        await api(`/tasks/${task.value.id}/approvals`, { method: "POST", body: JSON.stringify({ tool_name: "safe_log_cleanup", arguments: argumentsValue }) });
        return true;
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "清理申请失败";
        return false;
    }
}
async function confirmApproval(approval) {
    try {
        const reason = await ElMessageBox.prompt("确认执行此清理操作？请输入公开确认理由。", "清理确认", {
            confirmButtonText: "确认",
            cancelButtonText: "返回",
            inputPattern: /.+/,
            inputErrorMessage: "必须填写理由",
            type: "warning",
        });
        await api(`/approvals/${approval.id}/approve`, { method: "POST", body: JSON.stringify({ reason: reason.value }) });
        ElMessage.success("确认已写入审计链，可以执行清理");
        await loadApprovals();
        return true;
    }
    catch (e) {
        if (e !== "cancel" && e !== "close")
            error.value = e instanceof Error ? e.message : "确认失败";
        return false;
    }
}
async function confirmAndExecute(approval) {
    const confirmed = await confirmApproval(approval);
    if (!confirmed)
        return;
    const refreshed = approvals.value.find((item) => item.id === approval.id) || { ...approval, status: "APPROVED" };
    await executeApproved(refreshed);
}
function canSelectCleanup(value) {
    return Boolean(value.eligible && value.candidate?.candidate_id);
}
function isCleanupSelected(value) {
    const candidateId = value.candidate?.candidate_id;
    return Boolean(candidateId && selectedCandidateIds.value.includes(candidateId));
}
function toggleCleanup(value, checked) {
    const candidateId = value.candidate?.candidate_id;
    if (!candidateId)
        return;
    const selected = new Set(selectedCandidateIds.value);
    if (checked) {
        selected.add(candidateId);
    }
    else {
        selected.delete(candidateId);
    }
    selectedCandidateIds.value = [...selected];
}
function selectAllEligibleCleanup() {
    selectedCandidateIds.value = eligibleCleanupDecisions.value
        .map((item) => item.candidate?.candidate_id)
        .filter((item) => Boolean(item));
}
function selectDisposableCleanup() {
    const disposable = eligibleCleanupDecisions.value.filter(isDisposableCleanup);
    selectedCandidateIds.value = disposable
        .map((item) => item.candidate?.candidate_id)
        .filter((item) => Boolean(item));
    if (!disposable.length) {
        ElMessage.info("当前没有可智能选择的缓存、临时文件或下载目录安装包");
    }
    else {
        ElMessage.success(`已选择 ${disposable.length} 个缓存/临时文件候选`);
    }
}
function clearCleanupSelection() {
    selectedCandidateIds.value = [];
}
function isDisposableCleanup(value) {
    const file = fileForDecision(value);
    const classification = file?.classification || "";
    const path = (file?.path || "").toLowerCase();
    return (canSelectCleanup(value)
        && (classification === "DISPOSABLE_DOWNLOAD_OR_CACHE_CANDIDATE"
            || classification === "SAFE_LOG_OR_CACHE_CANDIDATE"
            || path.includes("/tmp/")
            || path.includes("/var/tmp/")
            || path.includes("/.cache/")
            || path.includes("/downloads/")
            || path.includes("\\tmp\\")
            || path.includes("\\downloads\\")));
}
async function loadApprovals() {
    if (task.value)
        approvals.value = await api(`/tasks/${task.value.id}/approvals`);
}
async function executeApproved(approval) {
    if (!task.value)
        return;
    try {
        const claimed = await api(`/approvals/${approval.id}/claim`, { method: "POST" });
        const argumentsValue = approval.arguments_summary.candidate_id ? { candidate_id: approval.arguments_summary.candidate_id } : approval.arguments_summary;
        const execution = await api("/executions/run", {
            method: "POST",
            body: JSON.stringify({ task_id: task.value.id, tool_name: approval.tool_name, arguments: argumentsValue, approval_token: claimed.approval_token }),
        });
        const cleanupCandidate = candidateForApproval(approval);
        if (approval.tool_name === "safe_log_cleanup" && cleanupCandidate) {
            executionSummaries.value.unshift({
                approval_id: approval.id,
                candidate_id: cleanupCandidate.candidate_id || "",
                path: cleanupCandidate.path,
                released_bytes: cleanupCandidate.size_bytes,
                verification: execution.verification,
            });
            ElMessage.success(`已清理 ${cleanupCandidate.path}，释放约 ${formatBytes(cleanupCandidate.size_bytes)}`);
        }
        else {
            ElMessage.success(`执行完成：${execution.verification}`);
        }
        await loadApprovals();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "执行失败";
    }
}
function candidateForApproval(approval) {
    const candidateId = approval.arguments_summary.candidate_id;
    if (!candidateId)
        return null;
    return (result.value?.cleanup_analysis || [])
        .map((item) => item.candidate)
        .find((candidate) => candidate?.candidate_id === candidateId) || null;
}
function openJson(title, value) {
    detailTitle.value = title;
    detailJson.value = JSON.stringify(value, null, 2);
    detailVisible.value = true;
}
function formatBytes(value) {
    if (value === undefined)
        return "—";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = value;
    let index = 0;
    while (size >= 1024 && index < units.length - 1) {
        size /= 1024;
        index += 1;
    }
    return `${size.toFixed(index ? 1 : 0)} ${units[index]}`;
}
function formatArgs(value) {
    const keys = Object.keys(value || {});
    if (!keys.length)
        return "无需参数";
    return keys.map((key) => `${key}=${String(value[key])}`).join("；");
}
function tagType(level) {
    return level === "critical" ? "danger" : level === "warning" ? "warning" : "success";
}
function levelText(level) {
    return { ok: "未发现异常", warning: "需要关注", critical: "异常/已阻断" }[level] || level;
}
function intentText(value) {
    return { QUERY: "查询", DIAGNOSIS: "故障诊断", INSPECTION: "安全巡检", CHANGE: "受控变更", CLEANUP: "清理分析", RECOVERY: "恢复", FORBIDDEN: "禁止请求" }[value] || value;
}
function toolTitle(value) {
    return {
        capability_probe: "能力探测",
        system_snapshot: "系统快照",
        process_list: "进程列表",
        zombie_process_scan: "僵尸进程扫描",
        network_socket_list: "监听端口",
        network_config_snapshot: "网络配置",
        port_owner_lookup: "端口归属",
        disk_usage_scan: "磁盘用量",
        large_file_scan: "大文件扫描",
        open_file_lookup: "文件占用",
        journal_query: "服务日志",
        service_status: "服务状态",
        config_drift_check: "配置漂移",
        io_diagnose: "I/O 诊断",
        security_baseline_scan: "安全基线",
        safe_log_cleanup: "清理候选文件",
    }[value] || value;
}
function causeTitle(value) {
    return { disk_pressure: "磁盘空间压力", high_cpu: "CPU/进程负载线索", zombie_process: "僵尸进程", service_failure: "服务故障", config_drift: "配置漂移" }[value] || value;
}
function reasonText(value) {
    return {
        SAFE_CANDIDATE: "满足清理候选规则",
        FILE_IS_OPEN: "文件正在使用",
        OPEN_FILE_STATE_UNKNOWN: "无法确认文件占用状态",
        CRITICAL_OR_DATABASE_LOG: "关键或数据库日志/敏感命名",
        RETENTION_PERIOD_NOT_MET: "未达到保留期",
        FILE_TYPE_NOT_ALLOWED: "文件类型不允许",
        BELOW_SIZE_THRESHOLD: "未达到清理阈值",
        PROTECTED_PATH: "受保护路径",
        PATH_REJECTED: "路径不在允许范围",
        STAT_FAILED: "无法读取文件状态",
        NOT_REGULAR_FILE: "不是普通文件",
    }[value] || value;
}
function fileForDecision(value) {
    return value.candidate || value.observed_file || null;
}
function candidateType(value) {
    return {
        DISPOSABLE_DOWNLOAD_OR_CACHE_CANDIDATE: "下载/临时文件",
        SAFE_LOG_OR_CACHE_CANDIDATE: "日志/缓存文件",
        OBSERVED_LARGE_FILE: "扫描到的大文件",
    }[String(value)] || "扫描到的大文件";
}
function evidenceType(value) {
    return { metric: "指标", file: "文件", process: "进程", service: "服务", log: "日志", network: "网络", config: "配置" }[value] || value;
}
function sourceText(value) {
    return {
        system_snapshot: "系统快照",
        disk_usage_scan: "磁盘用量扫描",
        large_file_scan: "大文件扫描",
        process_list: "进程列表",
        service_status: "服务状态",
        journal_query: "服务日志",
        network_socket_list: "监听端口",
        network_config_snapshot: "网络配置",
        port_owner_lookup: "端口归属",
    }[value] || value;
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_elements;
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['cleanup-toolbar-right']} */ ;
/** @type {__VLS_StyleScopedClasses['cleanup-execution-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['cleanup-execution-summary']} */ ;
// CSS variable injection
// CSS variable injection end
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "task-page" },
});
__VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
    ...{ class: "panel task-composer" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel-head" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({
    ...{ class: "mode-badge" },
});
(__VLS_ctx.zhStatus(__VLS_ctx.session.mode));
// @ts-ignore
[zhStatus, session,];
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "prompt-examples" },
});
for (const [example] of __VLS_getVForSourceType((__VLS_ctx.examples))) {
    // @ts-ignore
    [examples,];
    __VLS_asFunctionalElement(__VLS_elements.button, __VLS_elements.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.goal = example;
                // @ts-ignore
                [goal,];
            } },
        key: (example),
        type: "button",
    });
    (example);
}
const __VLS_0 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
ElInput;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onKeydown': {} },
    modelValue: (__VLS_ctx.goal),
    type: "textarea",
    rows: (5),
    maxlength: "4000",
    showWordLimit: true,
    placeholder: "例如：分析磁盘空间不足的原因，并列出安全清理候选。",
}));
const __VLS_2 = __VLS_1({
    ...{ 'onKeydown': {} },
    modelValue: (__VLS_ctx.goal),
    type: "textarea",
    rows: (5),
    maxlength: "4000",
    showWordLimit: true,
    placeholder: "例如：分析磁盘空间不足的原因，并列出安全清理候选。",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
const __VLS_6 = ({ keydown: {} },
    { onKeydown: (__VLS_ctx.run) });
// @ts-ignore
[goal, run,];
var __VLS_3;
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "composer-actions" },
});
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
const __VLS_8 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    ...{ 'onClick': {} },
    ...{ class: "task-primary" },
    type: "primary",
    loading: (__VLS_ctx.loading),
    disabled: (!__VLS_ctx.goal.trim()),
}));
const __VLS_10 = __VLS_9({
    ...{ 'onClick': {} },
    ...{ class: "task-primary" },
    type: "primary",
    loading: (__VLS_ctx.loading),
    disabled: (!__VLS_ctx.goal.trim()),
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
let __VLS_12;
let __VLS_13;
const __VLS_14 = ({ click: {} },
    { onClick: (__VLS_ctx.run) });
const { default: __VLS_15 } = __VLS_11.slots;
// @ts-ignore
[goal, run, loading,];
var __VLS_11;
if (__VLS_ctx.error) {
    // @ts-ignore
    [error,];
    const __VLS_16 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    ElAlert;
    // @ts-ignore
    const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
        title: (__VLS_ctx.error),
        type: "error",
        showIcon: true,
        closable: (false),
    }));
    const __VLS_18 = __VLS_17({
        title: (__VLS_ctx.error),
        type: "error",
        showIcon: true,
        closable: (false),
    }, ...__VLS_functionalComponentArgsRest(__VLS_17));
    // @ts-ignore
    [error,];
}
if (__VLS_ctx.result && __VLS_ctx.task) {
    // @ts-ignore
    [result, task,];
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel answer-panel" },
        ...{ class: (`answer-${__VLS_ctx.result.diagnosis.level}`) },
    });
    // @ts-ignore
    [result,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    (__VLS_ctx.task.goal);
    // @ts-ignore
    [task,];
    const __VLS_21 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    ElTag;
    // @ts-ignore
    const __VLS_22 = __VLS_asFunctionalComponent(__VLS_21, new __VLS_21({
        type: (__VLS_ctx.tagType(__VLS_ctx.result.diagnosis.level)),
    }));
    const __VLS_23 = __VLS_22({
        type: (__VLS_ctx.tagType(__VLS_ctx.result.diagnosis.level)),
    }, ...__VLS_functionalComponentArgsRest(__VLS_22));
    const { default: __VLS_25 } = __VLS_24.slots;
    // @ts-ignore
    [result, tagType,];
    (__VLS_ctx.levelText(__VLS_ctx.result.diagnosis.level));
    // @ts-ignore
    [result, levelText,];
    var __VLS_24;
    __VLS_asFunctionalElement(__VLS_elements.h2, __VLS_elements.h2)({});
    (__VLS_ctx.result.diagnosis.headline);
    // @ts-ignore
    [result,];
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({
        ...{ class: "answer-text" },
    });
    (__VLS_ctx.result.diagnosis.answer);
    // @ts-ignore
    [result,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "answer-grid" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({});
    __VLS_asFunctionalElement(__VLS_elements.ul, __VLS_elements.ul)({});
    for (const [item] of __VLS_getVForSourceType((__VLS_ctx.result.diagnosis.findings))) {
        // @ts-ignore
        [result,];
        __VLS_asFunctionalElement(__VLS_elements.li, __VLS_elements.li)({
            key: (item),
        });
        (item);
    }
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({});
    __VLS_asFunctionalElement(__VLS_elements.ul, __VLS_elements.ul)({});
    for (const [item] of __VLS_getVForSourceType((__VLS_ctx.result.diagnosis.recommendations))) {
        // @ts-ignore
        [result,];
        __VLS_asFunctionalElement(__VLS_elements.li, __VLS_elements.li)({
            key: (item),
        });
        (item);
    }
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "result-summary" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "summary-card" },
    });
    __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
    (__VLS_ctx.zhStatus(__VLS_ctx.result.status));
    // @ts-ignore
    [zhStatus, result,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "summary-card" },
    });
    __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
    (__VLS_ctx.intentText(__VLS_ctx.result.plan.intent));
    // @ts-ignore
    [result, intentText,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "summary-card" },
    });
    __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({
        ...{ class: (['risk-level', __VLS_ctx.result.plan.risk_level.toLowerCase()]) },
    });
    // @ts-ignore
    [result,];
    (__VLS_ctx.result.plan.risk_level);
    // @ts-ignore
    [result,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "summary-card" },
    });
    __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
    (__VLS_ctx.result.normalized_evidence.length);
    // @ts-ignore
    [result,];
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    const __VLS_26 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    ElTable;
    // @ts-ignore
    const __VLS_27 = __VLS_asFunctionalComponent(__VLS_26, new __VLS_26({
        data: (__VLS_ctx.result.plan.steps),
        emptyText: "安全策略已阻断，未生成工具调用计划",
    }));
    const __VLS_28 = __VLS_27({
        data: (__VLS_ctx.result.plan.steps),
        emptyText: "安全策略已阻断，未生成工具调用计划",
    }, ...__VLS_functionalComponentArgsRest(__VLS_27));
    const { default: __VLS_30 } = __VLS_29.slots;
    // @ts-ignore
    [result,];
    const __VLS_31 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_32 = __VLS_asFunctionalComponent(__VLS_31, new __VLS_31({
        prop: "sequence",
        label: "步骤",
        width: "80",
    }));
    const __VLS_33 = __VLS_32({
        prop: "sequence",
        label: "步骤",
        width: "80",
    }, ...__VLS_functionalComponentArgsRest(__VLS_32));
    const __VLS_36 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        label: "工具",
        width: "210",
    }));
    const __VLS_38 = __VLS_37({
        label: "工具",
        width: "210",
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    const { default: __VLS_40 } = __VLS_39.slots;
    {
        const { default: __VLS_41 } = __VLS_39.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_41);
        (__VLS_ctx.toolTitle(scope.row.tool_name));
        // @ts-ignore
        [toolTitle,];
    }
    var __VLS_39;
    const __VLS_42 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_43 = __VLS_asFunctionalComponent(__VLS_42, new __VLS_42({
        prop: "purpose",
        label: "目的",
    }));
    const __VLS_44 = __VLS_43({
        prop: "purpose",
        label: "目的",
    }, ...__VLS_functionalComponentArgsRest(__VLS_43));
    const __VLS_47 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_48 = __VLS_asFunctionalComponent(__VLS_47, new __VLS_47({
        label: "参数",
        minWidth: "180",
    }));
    const __VLS_49 = __VLS_48({
        label: "参数",
        minWidth: "180",
    }, ...__VLS_functionalComponentArgsRest(__VLS_48));
    const { default: __VLS_51 } = __VLS_50.slots;
    {
        const { default: __VLS_52 } = __VLS_50.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_52);
        (__VLS_ctx.formatArgs(scope.row.arguments));
        // @ts-ignore
        [formatArgs,];
    }
    var __VLS_50;
    var __VLS_29;
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel candidate-panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    const __VLS_53 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    ElTag;
    // @ts-ignore
    const __VLS_54 = __VLS_asFunctionalComponent(__VLS_53, new __VLS_53({
        type: "warning",
    }));
    const __VLS_55 = __VLS_54({
        type: "warning",
    }, ...__VLS_functionalComponentArgsRest(__VLS_54));
    const { default: __VLS_57 } = __VLS_56.slots;
    var __VLS_56;
    if (!__VLS_ctx.result.cleanup_analysis.length) {
        // @ts-ignore
        [result,];
        const __VLS_58 = {}.ElAlert;
        /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
        // @ts-ignore
        ElAlert;
        // @ts-ignore
        const __VLS_59 = __VLS_asFunctionalComponent(__VLS_58, new __VLS_58({
            title: "本次没有清理候选",
            description: "常见原因：本次不是清理类问题；允许目录没有超过 10 MB 的大文件；文件类型不在允许范围；文件位于保护路径；或文件正在使用。",
            type: "info",
            showIcon: true,
            closable: (false),
        }));
        const __VLS_60 = __VLS_59({
            title: "本次没有清理候选",
            description: "常见原因：本次不是清理类问题；允许目录没有超过 10 MB 的大文件；文件类型不在允许范围；文件位于保护路径；或文件正在使用。",
            type: "info",
            showIcon: true,
            closable: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_59));
    }
    if (__VLS_ctx.result.cleanup_analysis.length) {
        // @ts-ignore
        [result,];
        __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
            ...{ class: "cleanup-toolbar" },
        });
        __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
            ...{ class: "cleanup-toolbar-left" },
        });
        const __VLS_63 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_64 = __VLS_asFunctionalComponent(__VLS_63, new __VLS_63({
            ...{ 'onClick': {} },
            size: "small",
        }));
        const __VLS_65 = __VLS_64({
            ...{ 'onClick': {} },
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_64));
        let __VLS_67;
        let __VLS_68;
        const __VLS_69 = ({ click: {} },
            { onClick: (__VLS_ctx.selectAllEligibleCleanup) });
        const { default: __VLS_70 } = __VLS_66.slots;
        // @ts-ignore
        [selectAllEligibleCleanup,];
        var __VLS_66;
        const __VLS_71 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_72 = __VLS_asFunctionalComponent(__VLS_71, new __VLS_71({
            ...{ 'onClick': {} },
            size: "small",
            type: "warning",
            plain: true,
        }));
        const __VLS_73 = __VLS_72({
            ...{ 'onClick': {} },
            size: "small",
            type: "warning",
            plain: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_72));
        let __VLS_75;
        let __VLS_76;
        const __VLS_77 = ({ click: {} },
            { onClick: (__VLS_ctx.selectDisposableCleanup) });
        const { default: __VLS_78 } = __VLS_74.slots;
        // @ts-ignore
        [selectDisposableCleanup,];
        var __VLS_74;
        const __VLS_79 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_80 = __VLS_asFunctionalComponent(__VLS_79, new __VLS_79({
            ...{ 'onClick': {} },
            size: "small",
        }));
        const __VLS_81 = __VLS_80({
            ...{ 'onClick': {} },
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_80));
        let __VLS_83;
        let __VLS_84;
        const __VLS_85 = ({ click: {} },
            { onClick: (__VLS_ctx.clearCleanupSelection) });
        const { default: __VLS_86 } = __VLS_82.slots;
        // @ts-ignore
        [clearCleanupSelection,];
        var __VLS_82;
        __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
            ...{ class: "cleanup-toolbar-right" },
        });
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
        (__VLS_ctx.selectedCandidateIds.length);
        (__VLS_ctx.formatBytes(__VLS_ctx.selectedCleanupBytes));
        // @ts-ignore
        [selectedCandidateIds, formatBytes, selectedCleanupBytes,];
        const __VLS_87 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_88 = __VLS_asFunctionalComponent(__VLS_87, new __VLS_87({
            ...{ 'onClick': {} },
            size: "small",
            type: "primary",
            disabled: (!__VLS_ctx.selectedCandidateIds.length),
        }));
        const __VLS_89 = __VLS_88({
            ...{ 'onClick': {} },
            size: "small",
            type: "primary",
            disabled: (!__VLS_ctx.selectedCandidateIds.length),
        }, ...__VLS_functionalComponentArgsRest(__VLS_88));
        let __VLS_91;
        let __VLS_92;
        const __VLS_93 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(__VLS_ctx.result && __VLS_ctx.task))
                        return;
                    if (!(__VLS_ctx.result.cleanup_analysis.length))
                        return;
                    __VLS_ctx.requestSelectedCleanup();
                    // @ts-ignore
                    [selectedCandidateIds, requestSelectedCleanup,];
                } });
        const { default: __VLS_94 } = __VLS_90.slots;
        var __VLS_90;
    }
    if (__VLS_ctx.result.cleanup_analysis.length) {
        // @ts-ignore
        [result,];
        const __VLS_95 = {}.ElTable;
        /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
        // @ts-ignore
        ElTable;
        // @ts-ignore
        const __VLS_96 = __VLS_asFunctionalComponent(__VLS_95, new __VLS_95({
            data: (__VLS_ctx.result.cleanup_analysis),
        }));
        const __VLS_97 = __VLS_96({
            data: (__VLS_ctx.result.cleanup_analysis),
        }, ...__VLS_functionalComponentArgsRest(__VLS_96));
        const { default: __VLS_99 } = __VLS_98.slots;
        // @ts-ignore
        [result,];
        const __VLS_100 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
            label: "选择",
            width: "80",
        }));
        const __VLS_102 = __VLS_101({
            label: "选择",
            width: "80",
        }, ...__VLS_functionalComponentArgsRest(__VLS_101));
        const { default: __VLS_104 } = __VLS_103.slots;
        {
            const { default: __VLS_105 } = __VLS_103.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_105);
            const __VLS_106 = {}.ElCheckbox;
            /** @type {[typeof __VLS_components.ElCheckbox, typeof __VLS_components.elCheckbox, ]} */ ;
            // @ts-ignore
            ElCheckbox;
            // @ts-ignore
            const __VLS_107 = __VLS_asFunctionalComponent(__VLS_106, new __VLS_106({
                ...{ 'onChange': {} },
                modelValue: (__VLS_ctx.isCleanupSelected(scope.row)),
                disabled: (!__VLS_ctx.canSelectCleanup(scope.row)),
            }));
            const __VLS_108 = __VLS_107({
                ...{ 'onChange': {} },
                modelValue: (__VLS_ctx.isCleanupSelected(scope.row)),
                disabled: (!__VLS_ctx.canSelectCleanup(scope.row)),
            }, ...__VLS_functionalComponentArgsRest(__VLS_107));
            let __VLS_110;
            let __VLS_111;
            const __VLS_112 = ({ change: {} },
                { onChange: ((checked) => __VLS_ctx.toggleCleanup(scope.row, Boolean(checked))) });
            // @ts-ignore
            [isCleanupSelected, canSelectCleanup, toggleCleanup,];
            var __VLS_109;
        }
        var __VLS_103;
        const __VLS_114 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_115 = __VLS_asFunctionalComponent(__VLS_114, new __VLS_114({
            label: "判定",
            width: "120",
        }));
        const __VLS_116 = __VLS_115({
            label: "判定",
            width: "120",
        }, ...__VLS_functionalComponentArgsRest(__VLS_115));
        const { default: __VLS_118 } = __VLS_117.slots;
        {
            const { default: __VLS_119 } = __VLS_117.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_119);
            const __VLS_120 = {}.ElTag;
            /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
            // @ts-ignore
            ElTag;
            // @ts-ignore
            const __VLS_121 = __VLS_asFunctionalComponent(__VLS_120, new __VLS_120({
                type: (scope.row.eligible ? 'success' : 'danger'),
            }));
            const __VLS_122 = __VLS_121({
                type: (scope.row.eligible ? 'success' : 'danger'),
            }, ...__VLS_functionalComponentArgsRest(__VLS_121));
            const { default: __VLS_124 } = __VLS_123.slots;
            (scope.row.eligible ? "可处理" : "已排除");
            var __VLS_123;
        }
        var __VLS_117;
        const __VLS_125 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_126 = __VLS_asFunctionalComponent(__VLS_125, new __VLS_125({
            label: "类型",
            width: "170",
        }));
        const __VLS_127 = __VLS_126({
            label: "类型",
            width: "170",
        }, ...__VLS_functionalComponentArgsRest(__VLS_126));
        const { default: __VLS_129 } = __VLS_128.slots;
        {
            const { default: __VLS_130 } = __VLS_128.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_130);
            (__VLS_ctx.candidateType(__VLS_ctx.fileForDecision(scope.row)?.classification));
            // @ts-ignore
            [candidateType, fileForDecision,];
        }
        var __VLS_128;
        const __VLS_131 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_132 = __VLS_asFunctionalComponent(__VLS_131, new __VLS_131({
            label: "文件",
        }));
        const __VLS_133 = __VLS_132({
            label: "文件",
        }, ...__VLS_functionalComponentArgsRest(__VLS_132));
        const { default: __VLS_135 } = __VLS_134.slots;
        {
            const { default: __VLS_136 } = __VLS_134.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_136);
            (__VLS_ctx.fileForDecision(scope.row)?.path || "无法读取路径");
            // @ts-ignore
            [fileForDecision,];
        }
        var __VLS_134;
        const __VLS_137 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_138 = __VLS_asFunctionalComponent(__VLS_137, new __VLS_137({
            label: "大小",
            width: "130",
        }));
        const __VLS_139 = __VLS_138({
            label: "大小",
            width: "130",
        }, ...__VLS_functionalComponentArgsRest(__VLS_138));
        const { default: __VLS_141 } = __VLS_140.slots;
        {
            const { default: __VLS_142 } = __VLS_140.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_142);
            (__VLS_ctx.formatBytes(__VLS_ctx.fileForDecision(scope.row)?.size_bytes));
            // @ts-ignore
            [formatBytes, fileForDecision,];
        }
        var __VLS_140;
        const __VLS_143 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_144 = __VLS_asFunctionalComponent(__VLS_143, new __VLS_143({
            label: "规则结果",
            minWidth: "230",
        }));
        const __VLS_145 = __VLS_144({
            label: "规则结果",
            minWidth: "230",
        }, ...__VLS_functionalComponentArgsRest(__VLS_144));
        const { default: __VLS_147 } = __VLS_146.slots;
        {
            const { default: __VLS_148 } = __VLS_146.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_148);
            (scope.row.reason_codes.map(__VLS_ctx.reasonText).join("；"));
            // @ts-ignore
            [reasonText,];
        }
        var __VLS_146;
        const __VLS_149 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_150 = __VLS_asFunctionalComponent(__VLS_149, new __VLS_149({
            label: "详情",
            width: "100",
        }));
        const __VLS_151 = __VLS_150({
            label: "详情",
            width: "100",
        }, ...__VLS_functionalComponentArgsRest(__VLS_150));
        const { default: __VLS_153 } = __VLS_152.slots;
        {
            const { default: __VLS_154 } = __VLS_152.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_154);
            const __VLS_155 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_156 = __VLS_asFunctionalComponent(__VLS_155, new __VLS_155({
                ...{ 'onClick': {} },
                size: "small",
            }));
            const __VLS_157 = __VLS_156({
                ...{ 'onClick': {} },
                size: "small",
            }, ...__VLS_functionalComponentArgsRest(__VLS_156));
            let __VLS_159;
            let __VLS_160;
            const __VLS_161 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.result && __VLS_ctx.task))
                            return;
                        if (!(__VLS_ctx.result.cleanup_analysis.length))
                            return;
                        __VLS_ctx.openJson('清理候选详情', scope.row);
                        // @ts-ignore
                        [openJson,];
                    } });
            const { default: __VLS_162 } = __VLS_158.slots;
            var __VLS_158;
        }
        var __VLS_152;
        const __VLS_163 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_164 = __VLS_asFunctionalComponent(__VLS_163, new __VLS_163({
            label: "操作",
            width: "160",
        }));
        const __VLS_165 = __VLS_164({
            label: "操作",
            width: "160",
        }, ...__VLS_functionalComponentArgsRest(__VLS_164));
        const { default: __VLS_167 } = __VLS_166.slots;
        {
            const { default: __VLS_168 } = __VLS_166.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_168);
            const __VLS_169 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_170 = __VLS_asFunctionalComponent(__VLS_169, new __VLS_169({
                ...{ 'onClick': {} },
                size: "small",
                type: "primary",
                disabled: (!scope.row.eligible),
            }));
            const __VLS_171 = __VLS_170({
                ...{ 'onClick': {} },
                size: "small",
                type: "primary",
                disabled: (!scope.row.eligible),
            }, ...__VLS_functionalComponentArgsRest(__VLS_170));
            let __VLS_173;
            let __VLS_174;
            const __VLS_175 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.result && __VLS_ctx.task))
                            return;
                        if (!(__VLS_ctx.result.cleanup_analysis.length))
                            return;
                        __VLS_ctx.requestCleanup(scope.row.candidate);
                        // @ts-ignore
                        [requestCleanup,];
                    } });
            const { default: __VLS_176 } = __VLS_172.slots;
            var __VLS_172;
        }
        var __VLS_166;
        var __VLS_98;
    }
    if (__VLS_ctx.executionSummaries.length) {
        // @ts-ignore
        [executionSummaries,];
        __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
            ...{ class: "cleanup-execution-summary" },
        });
        __VLS_asFunctionalElement(__VLS_elements.h4, __VLS_elements.h4)({});
        __VLS_asFunctionalElement(__VLS_elements.ul, __VLS_elements.ul)({});
        for (const [item] of __VLS_getVForSourceType((__VLS_ctx.executionSummaries))) {
            // @ts-ignore
            [executionSummaries,];
            __VLS_asFunctionalElement(__VLS_elements.li, __VLS_elements.li)({
                key: (item.approval_id),
            });
            (item.path);
            (__VLS_ctx.formatBytes(item.released_bytes));
            (item.verification);
            // @ts-ignore
            [formatBytes,];
        }
    }
    if (__VLS_ctx.approvals.length) {
        // @ts-ignore
        [approvals,];
        __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
            ...{ class: "panel" },
        });
        __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
            ...{ class: "panel-head" },
        });
        __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
        __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
        __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
        const __VLS_177 = {}.ElTable;
        /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
        // @ts-ignore
        ElTable;
        // @ts-ignore
        const __VLS_178 = __VLS_asFunctionalComponent(__VLS_177, new __VLS_177({
            data: (__VLS_ctx.approvals),
        }));
        const __VLS_179 = __VLS_178({
            data: (__VLS_ctx.approvals),
        }, ...__VLS_functionalComponentArgsRest(__VLS_178));
        const { default: __VLS_181 } = __VLS_180.slots;
        // @ts-ignore
        [approvals,];
        const __VLS_182 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_183 = __VLS_asFunctionalComponent(__VLS_182, new __VLS_182({
            label: "工具",
            width: "180",
        }));
        const __VLS_184 = __VLS_183({
            label: "工具",
            width: "180",
        }, ...__VLS_functionalComponentArgsRest(__VLS_183));
        const { default: __VLS_186 } = __VLS_185.slots;
        {
            const { default: __VLS_187 } = __VLS_185.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_187);
            (__VLS_ctx.toolTitle(scope.row.tool_name));
            // @ts-ignore
            [toolTitle,];
        }
        var __VLS_185;
        const __VLS_188 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_189 = __VLS_asFunctionalComponent(__VLS_188, new __VLS_188({
            prop: "risk_level",
            label: "风险",
            width: "90",
        }));
        const __VLS_190 = __VLS_189({
            prop: "risk_level",
            label: "风险",
            width: "90",
        }, ...__VLS_functionalComponentArgsRest(__VLS_189));
        const __VLS_193 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_194 = __VLS_asFunctionalComponent(__VLS_193, new __VLS_193({
            label: "状态",
            width: "120",
        }));
        const __VLS_195 = __VLS_194({
            label: "状态",
            width: "120",
        }, ...__VLS_functionalComponentArgsRest(__VLS_194));
        const { default: __VLS_197 } = __VLS_196.slots;
        {
            const { default: __VLS_198 } = __VLS_196.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_198);
            (__VLS_ctx.zhStatus(scope.row.status));
            // @ts-ignore
            [zhStatus,];
        }
        var __VLS_196;
        const __VLS_199 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_200 = __VLS_asFunctionalComponent(__VLS_199, new __VLS_199({
            label: "参数",
        }));
        const __VLS_201 = __VLS_200({
            label: "参数",
        }, ...__VLS_functionalComponentArgsRest(__VLS_200));
        const { default: __VLS_203 } = __VLS_202.slots;
        {
            const { default: __VLS_204 } = __VLS_202.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_204);
            (__VLS_ctx.formatArgs(scope.row.arguments_summary));
            // @ts-ignore
            [formatArgs,];
        }
        var __VLS_202;
        const __VLS_205 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_206 = __VLS_asFunctionalComponent(__VLS_205, new __VLS_205({
            label: "执行",
            width: "220",
        }));
        const __VLS_207 = __VLS_206({
            label: "执行",
            width: "220",
        }, ...__VLS_functionalComponentArgsRest(__VLS_206));
        const { default: __VLS_209 } = __VLS_208.slots;
        {
            const { default: __VLS_210 } = __VLS_208.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_210);
            if (scope.row.status === 'PENDING') {
                const __VLS_211 = {}.ElButton;
                /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
                // @ts-ignore
                ElButton;
                // @ts-ignore
                const __VLS_212 = __VLS_asFunctionalComponent(__VLS_211, new __VLS_211({
                    ...{ 'onClick': {} },
                    size: "small",
                    type: "warning",
                }));
                const __VLS_213 = __VLS_212({
                    ...{ 'onClick': {} },
                    size: "small",
                    type: "warning",
                }, ...__VLS_functionalComponentArgsRest(__VLS_212));
                let __VLS_215;
                let __VLS_216;
                const __VLS_217 = ({ click: {} },
                    { onClick: (...[$event]) => {
                            if (!(__VLS_ctx.result && __VLS_ctx.task))
                                return;
                            if (!(__VLS_ctx.approvals.length))
                                return;
                            if (!(scope.row.status === 'PENDING'))
                                return;
                            __VLS_ctx.confirmApproval(scope.row);
                            // @ts-ignore
                            [confirmApproval,];
                        } });
                const { default: __VLS_218 } = __VLS_214.slots;
                var __VLS_214;
                const __VLS_219 = {}.ElButton;
                /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
                // @ts-ignore
                ElButton;
                // @ts-ignore
                const __VLS_220 = __VLS_asFunctionalComponent(__VLS_219, new __VLS_219({
                    ...{ 'onClick': {} },
                    size: "small",
                    type: "success",
                }));
                const __VLS_221 = __VLS_220({
                    ...{ 'onClick': {} },
                    size: "small",
                    type: "success",
                }, ...__VLS_functionalComponentArgsRest(__VLS_220));
                let __VLS_223;
                let __VLS_224;
                const __VLS_225 = ({ click: {} },
                    { onClick: (...[$event]) => {
                            if (!(__VLS_ctx.result && __VLS_ctx.task))
                                return;
                            if (!(__VLS_ctx.approvals.length))
                                return;
                            if (!(scope.row.status === 'PENDING'))
                                return;
                            __VLS_ctx.confirmAndExecute(scope.row);
                            // @ts-ignore
                            [confirmAndExecute,];
                        } });
                const { default: __VLS_226 } = __VLS_222.slots;
                var __VLS_222;
            }
            else {
                const __VLS_227 = {}.ElButton;
                /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
                // @ts-ignore
                ElButton;
                // @ts-ignore
                const __VLS_228 = __VLS_asFunctionalComponent(__VLS_227, new __VLS_227({
                    ...{ 'onClick': {} },
                    size: "small",
                    type: "success",
                    disabled: (scope.row.status !== 'APPROVED'),
                }));
                const __VLS_229 = __VLS_228({
                    ...{ 'onClick': {} },
                    size: "small",
                    type: "success",
                    disabled: (scope.row.status !== 'APPROVED'),
                }, ...__VLS_functionalComponentArgsRest(__VLS_228));
                let __VLS_231;
                let __VLS_232;
                const __VLS_233 = ({ click: {} },
                    { onClick: (...[$event]) => {
                            if (!(__VLS_ctx.result && __VLS_ctx.task))
                                return;
                            if (!(__VLS_ctx.approvals.length))
                                return;
                            if (!!(scope.row.status === 'PENDING'))
                                return;
                            __VLS_ctx.executeApproved(scope.row);
                            // @ts-ignore
                            [executeApproved,];
                        } });
                const { default: __VLS_234 } = __VLS_230.slots;
                var __VLS_230;
            }
        }
        var __VLS_208;
        var __VLS_180;
    }
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "task-columns" },
    });
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    if (__VLS_ctx.result.root_causes.length) {
        // @ts-ignore
        [result,];
        __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
            ...{ class: "rca-list" },
        });
        for (const [cause, index] of __VLS_getVForSourceType((__VLS_ctx.result.root_causes))) {
            // @ts-ignore
            [result,];
            __VLS_asFunctionalElement(__VLS_elements.article, __VLS_elements.article)({
                key: (cause.title),
                ...{ class: "rca-card" },
            });
            __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({
                ...{ class: "rank" },
            });
            (index + 1);
            __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
            __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
            (__VLS_ctx.causeTitle(cause.title));
            // @ts-ignore
            [causeTitle,];
            __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
            (cause.reason_summary);
            __VLS_asFunctionalElement(__VLS_elements.small, __VLS_elements.small)({});
            (cause.recommended_actions.join("；"));
            const __VLS_235 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_236 = __VLS_asFunctionalComponent(__VLS_235, new __VLS_235({
                ...{ 'onClick': {} },
                text: true,
                type: "primary",
            }));
            const __VLS_237 = __VLS_236({
                ...{ 'onClick': {} },
                text: true,
                type: "primary",
            }, ...__VLS_functionalComponentArgsRest(__VLS_236));
            let __VLS_239;
            let __VLS_240;
            const __VLS_241 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.result && __VLS_ctx.task))
                            return;
                        if (!(__VLS_ctx.result.root_causes.length))
                            return;
                        __VLS_ctx.openJson('根因候选详情', cause);
                        // @ts-ignore
                        [openJson,];
                    } });
            const { default: __VLS_242 } = __VLS_238.slots;
            var __VLS_238;
            __VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({});
            (Math.round(cause.confidence * 100));
        }
    }
    else {
        const __VLS_243 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        ElEmpty;
        // @ts-ignore
        const __VLS_244 = __VLS_asFunctionalComponent(__VLS_243, new __VLS_243({
            description: "当前证据不足以生成根因候选。",
        }));
        const __VLS_245 = __VLS_244({
            description: "当前证据不足以生成根因候选。",
        }, ...__VLS_functionalComponentArgsRest(__VLS_244));
    }
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    const __VLS_248 = {}.ElTimeline;
    /** @type {[typeof __VLS_components.ElTimeline, typeof __VLS_components.elTimeline, typeof __VLS_components.ElTimeline, typeof __VLS_components.elTimeline, ]} */ ;
    // @ts-ignore
    ElTimeline;
    // @ts-ignore
    const __VLS_249 = __VLS_asFunctionalComponent(__VLS_248, new __VLS_248({
        ...{ class: "decision-timeline" },
    }));
    const __VLS_250 = __VLS_249({
        ...{ class: "decision-timeline" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_249));
    const { default: __VLS_252 } = __VLS_251.slots;
    for (const [item] of __VLS_getVForSourceType((__VLS_ctx.result.decision_chain))) {
        // @ts-ignore
        [result,];
        const __VLS_253 = {}.ElTimelineItem;
        /** @type {[typeof __VLS_components.ElTimelineItem, typeof __VLS_components.elTimelineItem, typeof __VLS_components.ElTimelineItem, typeof __VLS_components.elTimelineItem, ]} */ ;
        // @ts-ignore
        ElTimelineItem;
        // @ts-ignore
        const __VLS_254 = __VLS_asFunctionalComponent(__VLS_253, new __VLS_253({
            key: (item.stage),
            type: (item.reason_code === 'FORBIDDEN_INPUT' ? 'danger' : 'primary'),
        }));
        const __VLS_255 = __VLS_254({
            key: (item.stage),
            type: (item.reason_code === 'FORBIDDEN_INPUT' ? 'danger' : 'primary'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_254));
        const { default: __VLS_257 } = __VLS_256.slots;
        __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
        (item.stage);
        __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
        (item.summary);
        __VLS_asFunctionalElement(__VLS_elements.code, __VLS_elements.code)({});
        (item.reason_code);
        var __VLS_256;
    }
    var __VLS_251;
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    const __VLS_258 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    ElTable;
    // @ts-ignore
    const __VLS_259 = __VLS_asFunctionalComponent(__VLS_258, new __VLS_258({
        data: (__VLS_ctx.result.normalized_evidence),
        maxHeight: "420",
        emptyText: "暂无标准化证据",
    }));
    const __VLS_260 = __VLS_259({
        data: (__VLS_ctx.result.normalized_evidence),
        maxHeight: "420",
        emptyText: "暂无标准化证据",
    }, ...__VLS_functionalComponentArgsRest(__VLS_259));
    const { default: __VLS_262 } = __VLS_261.slots;
    // @ts-ignore
    [result,];
    const __VLS_263 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_264 = __VLS_asFunctionalComponent(__VLS_263, new __VLS_263({
        label: "类型",
        width: "110",
    }));
    const __VLS_265 = __VLS_264({
        label: "类型",
        width: "110",
    }, ...__VLS_functionalComponentArgsRest(__VLS_264));
    const { default: __VLS_267 } = __VLS_266.slots;
    {
        const { default: __VLS_268 } = __VLS_266.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_268);
        (__VLS_ctx.evidenceType(scope.row.evidence_type));
        // @ts-ignore
        [evidenceType,];
    }
    var __VLS_266;
    const __VLS_269 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_270 = __VLS_asFunctionalComponent(__VLS_269, new __VLS_269({
        label: "数据来源",
        width: "180",
    }));
    const __VLS_271 = __VLS_270({
        label: "数据来源",
        width: "180",
    }, ...__VLS_functionalComponentArgsRest(__VLS_270));
    const { default: __VLS_273 } = __VLS_272.slots;
    {
        const { default: __VLS_274 } = __VLS_272.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_274);
        (__VLS_ctx.sourceText(scope.row.source));
        // @ts-ignore
        [sourceText,];
    }
    var __VLS_272;
    const __VLS_275 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_276 = __VLS_asFunctionalComponent(__VLS_275, new __VLS_275({
        prop: "title",
        label: "证据",
    }));
    const __VLS_277 = __VLS_276({
        prop: "title",
        label: "证据",
    }, ...__VLS_functionalComponentArgsRest(__VLS_276));
    const __VLS_280 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_281 = __VLS_asFunctionalComponent(__VLS_280, new __VLS_280({
        prop: "value",
        label: "值",
    }));
    const __VLS_282 = __VLS_281({
        prop: "value",
        label: "值",
    }, ...__VLS_functionalComponentArgsRest(__VLS_281));
    const __VLS_285 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_286 = __VLS_asFunctionalComponent(__VLS_285, new __VLS_285({
        label: "异常度",
        width: "110",
    }));
    const __VLS_287 = __VLS_286({
        label: "异常度",
        width: "110",
    }, ...__VLS_functionalComponentArgsRest(__VLS_286));
    const { default: __VLS_289 } = __VLS_288.slots;
    {
        const { default: __VLS_290 } = __VLS_288.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_290);
        (Math.round(scope.row.anomaly_score * 100));
    }
    var __VLS_288;
    const __VLS_291 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_292 = __VLS_asFunctionalComponent(__VLS_291, new __VLS_291({
        label: "信任标记",
        width: "160",
    }));
    const __VLS_293 = __VLS_292({
        label: "信任标记",
        width: "160",
    }, ...__VLS_functionalComponentArgsRest(__VLS_292));
    const { default: __VLS_295 } = __VLS_294.slots;
    {
        const { default: __VLS_296 } = __VLS_294.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_296);
        (scope.row.trust_label === "UNTRUSTED_DATA" ? "不可信外部数据" : scope.row.trust_label);
    }
    var __VLS_294;
    const __VLS_297 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_298 = __VLS_asFunctionalComponent(__VLS_297, new __VLS_297({
        label: "详情",
        width: "100",
    }));
    const __VLS_299 = __VLS_298({
        label: "详情",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_298));
    const { default: __VLS_301 } = __VLS_300.slots;
    {
        const { default: __VLS_302 } = __VLS_300.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_302);
        const __VLS_303 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_304 = __VLS_asFunctionalComponent(__VLS_303, new __VLS_303({
            ...{ 'onClick': {} },
            size: "small",
        }));
        const __VLS_305 = __VLS_304({
            ...{ 'onClick': {} },
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_304));
        let __VLS_307;
        let __VLS_308;
        const __VLS_309 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(__VLS_ctx.result && __VLS_ctx.task))
                        return;
                    __VLS_ctx.openJson('标准化证据详情', scope.row);
                    // @ts-ignore
                    [openJson,];
                } });
        const { default: __VLS_310 } = __VLS_306.slots;
        var __VLS_306;
    }
    var __VLS_300;
    var __VLS_261;
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    const __VLS_311 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    ElTable;
    // @ts-ignore
    const __VLS_312 = __VLS_asFunctionalComponent(__VLS_311, new __VLS_311({
        data: (__VLS_ctx.result.evidence),
        emptyText: "未调用工具",
    }));
    const __VLS_313 = __VLS_312({
        data: (__VLS_ctx.result.evidence),
        emptyText: "未调用工具",
    }, ...__VLS_functionalComponentArgsRest(__VLS_312));
    const { default: __VLS_315 } = __VLS_314.slots;
    // @ts-ignore
    [result,];
    const __VLS_316 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_317 = __VLS_asFunctionalComponent(__VLS_316, new __VLS_316({
        label: "工具",
        width: "210",
    }));
    const __VLS_318 = __VLS_317({
        label: "工具",
        width: "210",
    }, ...__VLS_functionalComponentArgsRest(__VLS_317));
    const { default: __VLS_320 } = __VLS_319.slots;
    {
        const { default: __VLS_321 } = __VLS_319.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_321);
        (__VLS_ctx.toolTitle(scope.row.tool_name));
        // @ts-ignore
        [toolTitle,];
    }
    var __VLS_319;
    const __VLS_322 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_323 = __VLS_asFunctionalComponent(__VLS_322, new __VLS_322({
        label: "信任标记",
        width: "180",
    }));
    const __VLS_324 = __VLS_323({
        label: "信任标记",
        width: "180",
    }, ...__VLS_functionalComponentArgsRest(__VLS_323));
    const { default: __VLS_326 } = __VLS_325.slots;
    {
        const { default: __VLS_327 } = __VLS_325.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_327);
        (scope.row.trust_label === "UNTRUSTED_DATA" ? "不可信外部数据" : scope.row.trust_label);
    }
    var __VLS_325;
    const __VLS_328 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_329 = __VLS_asFunctionalComponent(__VLS_328, new __VLS_328({
        label: "注入风险",
        width: "110",
    }));
    const __VLS_330 = __VLS_329({
        label: "注入风险",
        width: "110",
    }, ...__VLS_functionalComponentArgsRest(__VLS_329));
    const { default: __VLS_332 } = __VLS_331.slots;
    {
        const { default: __VLS_333 } = __VLS_331.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_333);
        const __VLS_334 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        ElTag;
        // @ts-ignore
        const __VLS_335 = __VLS_asFunctionalComponent(__VLS_334, new __VLS_334({
            type: (scope.row.injection_suspected ? 'danger' : 'success'),
        }));
        const __VLS_336 = __VLS_335({
            type: (scope.row.injection_suspected ? 'danger' : 'success'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_335));
        const { default: __VLS_338 } = __VLS_337.slots;
        (scope.row.injection_suspected ? "疑似" : "未发现");
        var __VLS_337;
    }
    var __VLS_331;
    const __VLS_339 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_340 = __VLS_asFunctionalComponent(__VLS_339, new __VLS_339({
        label: "回执",
        width: "100",
    }));
    const __VLS_341 = __VLS_340({
        label: "回执",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_340));
    const { default: __VLS_343 } = __VLS_342.slots;
    {
        const { default: __VLS_344 } = __VLS_342.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_344);
        const __VLS_345 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_346 = __VLS_asFunctionalComponent(__VLS_345, new __VLS_345({
            ...{ 'onClick': {} },
            size: "small",
        }));
        const __VLS_347 = __VLS_346({
            ...{ 'onClick': {} },
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_346));
        let __VLS_349;
        let __VLS_350;
        const __VLS_351 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(__VLS_ctx.result && __VLS_ctx.task))
                        return;
                    __VLS_ctx.openJson('原始工具回执', scope.row.payload);
                    // @ts-ignore
                    [openJson,];
                } });
        const { default: __VLS_352 } = __VLS_348.slots;
        var __VLS_348;
    }
    var __VLS_342;
    var __VLS_314;
}
const __VLS_353 = {}.ElDrawer;
/** @type {[typeof __VLS_components.ElDrawer, typeof __VLS_components.elDrawer, typeof __VLS_components.ElDrawer, typeof __VLS_components.elDrawer, ]} */ ;
// @ts-ignore
ElDrawer;
// @ts-ignore
const __VLS_354 = __VLS_asFunctionalComponent(__VLS_353, new __VLS_353({
    modelValue: (__VLS_ctx.detailVisible),
    title: (__VLS_ctx.detailTitle),
    size: "46%",
}));
const __VLS_355 = __VLS_354({
    modelValue: (__VLS_ctx.detailVisible),
    title: (__VLS_ctx.detailTitle),
    size: "46%",
}, ...__VLS_functionalComponentArgsRest(__VLS_354));
const { default: __VLS_357 } = __VLS_356.slots;
// @ts-ignore
[detailVisible, detailTitle,];
__VLS_asFunctionalElement(__VLS_elements.pre, __VLS_elements.pre)({});
(__VLS_ctx.detailJson);
// @ts-ignore
[detailJson,];
var __VLS_356;
/** @type {__VLS_StyleScopedClasses['task-page']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['task-composer']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['mode-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['prompt-examples']} */ ;
/** @type {__VLS_StyleScopedClasses['composer-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['task-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['answer-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['answer-text']} */ ;
/** @type {__VLS_StyleScopedClasses['answer-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['result-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['risk-level']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['candidate-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['cleanup-toolbar']} */ ;
/** @type {__VLS_StyleScopedClasses['cleanup-toolbar-left']} */ ;
/** @type {__VLS_StyleScopedClasses['cleanup-toolbar-right']} */ ;
/** @type {__VLS_StyleScopedClasses['cleanup-execution-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['task-columns']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['rca-list']} */ ;
/** @type {__VLS_StyleScopedClasses['rca-card']} */ ;
/** @type {__VLS_StyleScopedClasses['rank']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['decision-timeline']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        zhStatus: zhStatus,
        session: session,
        examples: examples,
        goal: goal,
        task: task,
        result: result,
        approvals: approvals,
        error: error,
        loading: loading,
        detailVisible: detailVisible,
        detailTitle: detailTitle,
        detailJson: detailJson,
        selectedCandidateIds: selectedCandidateIds,
        executionSummaries: executionSummaries,
        selectedCleanupBytes: selectedCleanupBytes,
        run: run,
        requestCleanup: requestCleanup,
        requestSelectedCleanup: requestSelectedCleanup,
        confirmApproval: confirmApproval,
        confirmAndExecute: confirmAndExecute,
        canSelectCleanup: canSelectCleanup,
        isCleanupSelected: isCleanupSelected,
        toggleCleanup: toggleCleanup,
        selectAllEligibleCleanup: selectAllEligibleCleanup,
        selectDisposableCleanup: selectDisposableCleanup,
        clearCleanupSelection: clearCleanupSelection,
        executeApproved: executeApproved,
        openJson: openJson,
        formatBytes: formatBytes,
        formatArgs: formatArgs,
        tagType: tagType,
        levelText: levelText,
        intentText: intentText,
        toolTitle: toolTitle,
        causeTitle: causeTitle,
        reasonText: reasonText,
        fileForDecision: fileForDecision,
        candidateType: candidateType,
        evidenceType: evidenceType,
        sourceText: sourceText,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
