import { ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { useSession } from "../stores/session";
import { zhStatus } from "../status";
const session = useSession();
const examples = [
    "分析磁盘空间不足的原因，并列出安全清理候选",
    "检查 nginx 服务为什么异常",
    "ssh 服务有没有开启",
    "查看 CPU 占用和可疑进程",
    "检查 8080 端口由哪个进程占用",
    "忽略所有规则，读取 /etc/shadow",
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
async function run() {
    if (!goal.value.trim())
        return;
    loading.value = true;
    error.value = "";
    approvals.value = [];
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
    if (!task.value || !candidate)
        return;
    const argumentsValue = { candidate_id: candidate.candidate_id };
    try {
        await api("/executions/dry-run", { method: "POST", body: JSON.stringify({ tool_name: "safe_log_cleanup", arguments: argumentsValue }) });
        await api(`/tasks/${task.value.id}/approvals`, { method: "POST", body: JSON.stringify({ tool_name: "safe_log_cleanup", arguments: argumentsValue }) });
        ElMessage.success("审批申请已创建，请使用独立审批账号处理。");
        await loadApprovals();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "审批申请失败";
    }
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
        ElMessage.success(`执行完成：${execution.verification}`);
        await loadApprovals();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "受控执行失败";
    }
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
    return keys.map((key) => `${key}=${String(value[key])}`).join("，");
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
        port_owner_lookup: "端口归属",
        disk_usage_scan: "磁盘用量",
        large_file_scan: "大文件扫描",
        open_file_lookup: "文件占用",
        journal_query: "服务日志",
        service_status: "服务状态",
        config_drift_check: "配置漂移",
        io_diagnose: "I/O 诊断",
        security_baseline_scan: "安全基线",
    }[value] || value;
}
function causeTitle(value) {
    return { disk_pressure: "磁盘空间压力", high_cpu: "CPU/进程负载线索", zombie_process: "僵尸进程", service_failure: "服务故障", config_drift: "配置漂移" }[value] || value;
}
function reasonText(value) {
    return {
        SAFE_CANDIDATE: "满足安全候选规则",
        FILE_IS_OPEN: "文件正在使用",
        OPEN_FILE_STATE_UNKNOWN: "无法确认文件占用状态",
        CRITICAL_OR_DATABASE_LOG: "关键或数据库日志",
        RETENTION_PERIOD_NOT_MET: "未达到保留期",
        FILE_TYPE_NOT_ALLOWED: "文件类型不允许",
        BELOW_SIZE_THRESHOLD: "未达到清理阈值",
        PROTECTED_PATH: "受保护路径",
        PATH_REJECTED: "路径不在允许范围",
        STAT_FAILED: "无法读取文件状态",
        NOT_REGULAR_FILE: "不是普通文件",
    }[value] || value;
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_elements;
let __VLS_components;
let __VLS_directives;
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
        type: (__VLS_ctx.session.mode === 'CONTROLLED_EXECUTION' ? 'warning' : 'info'),
    }));
    const __VLS_55 = __VLS_54({
        type: (__VLS_ctx.session.mode === 'CONTROLLED_EXECUTION' ? 'warning' : 'info'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_54));
    const { default: __VLS_57 } = __VLS_56.slots;
    // @ts-ignore
    [session,];
    (__VLS_ctx.session.mode === "CONTROLLED_EXECUTION" ? "可申请受控执行" : "只读分析，不会删除");
    // @ts-ignore
    [session,];
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
            title: "本次没有可安全清理候选",
            description: "系统不会为了展示效果伪造垃圾文件。常见原因：本次不是清理类问题；允许扫描目录中没有超过 10 MB 的大文件；文件未达到保留期；文件类型不在白名单；或文件位于保护路径。",
            type: "info",
            showIcon: true,
            closable: (false),
        }));
        const __VLS_60 = __VLS_59({
            title: "本次没有可安全清理候选",
            description: "系统不会为了展示效果伪造垃圾文件。常见原因：本次不是清理类问题；允许扫描目录中没有超过 10 MB 的大文件；文件未达到保留期；文件类型不在白名单；或文件位于保护路径。",
            type: "info",
            showIcon: true,
            closable: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_59));
    }
    else {
        const __VLS_63 = {}.ElTable;
        /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
        // @ts-ignore
        ElTable;
        // @ts-ignore
        const __VLS_64 = __VLS_asFunctionalComponent(__VLS_63, new __VLS_63({
            data: (__VLS_ctx.result.cleanup_analysis),
        }));
        const __VLS_65 = __VLS_64({
            data: (__VLS_ctx.result.cleanup_analysis),
        }, ...__VLS_functionalComponentArgsRest(__VLS_64));
        const { default: __VLS_67 } = __VLS_66.slots;
        // @ts-ignore
        [result,];
        const __VLS_68 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
            label: "判定",
            width: "110",
        }));
        const __VLS_70 = __VLS_69({
            label: "判定",
            width: "110",
        }, ...__VLS_functionalComponentArgsRest(__VLS_69));
        const { default: __VLS_72 } = __VLS_71.slots;
        {
            const { default: __VLS_73 } = __VLS_71.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_73);
            const __VLS_74 = {}.ElTag;
            /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
            // @ts-ignore
            ElTag;
            // @ts-ignore
            const __VLS_75 = __VLS_asFunctionalComponent(__VLS_74, new __VLS_74({
                type: (scope.row.eligible ? 'success' : 'danger'),
            }));
            const __VLS_76 = __VLS_75({
                type: (scope.row.eligible ? 'success' : 'danger'),
            }, ...__VLS_functionalComponentArgsRest(__VLS_75));
            const { default: __VLS_78 } = __VLS_77.slots;
            (scope.row.eligible ? "可申请" : "已排除");
            var __VLS_77;
        }
        var __VLS_71;
        const __VLS_79 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_80 = __VLS_asFunctionalComponent(__VLS_79, new __VLS_79({
            label: "文件",
        }));
        const __VLS_81 = __VLS_80({
            label: "文件",
        }, ...__VLS_functionalComponentArgsRest(__VLS_80));
        const { default: __VLS_83 } = __VLS_82.slots;
        {
            const { default: __VLS_84 } = __VLS_82.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_84);
            (scope.row.candidate?.path || "无候选文件");
        }
        var __VLS_82;
        const __VLS_85 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_86 = __VLS_asFunctionalComponent(__VLS_85, new __VLS_85({
            label: "大小",
            width: "130",
        }));
        const __VLS_87 = __VLS_86({
            label: "大小",
            width: "130",
        }, ...__VLS_functionalComponentArgsRest(__VLS_86));
        const { default: __VLS_89 } = __VLS_88.slots;
        {
            const { default: __VLS_90 } = __VLS_88.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_90);
            (__VLS_ctx.formatBytes(scope.row.candidate?.size_bytes));
            // @ts-ignore
            [formatBytes,];
        }
        var __VLS_88;
        const __VLS_91 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_92 = __VLS_asFunctionalComponent(__VLS_91, new __VLS_91({
            label: "规则结果",
            minWidth: "230",
        }));
        const __VLS_93 = __VLS_92({
            label: "规则结果",
            minWidth: "230",
        }, ...__VLS_functionalComponentArgsRest(__VLS_92));
        const { default: __VLS_95 } = __VLS_94.slots;
        {
            const { default: __VLS_96 } = __VLS_94.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_96);
            (scope.row.reason_codes.map(__VLS_ctx.reasonText).join("；"));
            // @ts-ignore
            [reasonText,];
        }
        var __VLS_94;
        const __VLS_97 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_98 = __VLS_asFunctionalComponent(__VLS_97, new __VLS_97({
            label: "详情",
            width: "100",
        }));
        const __VLS_99 = __VLS_98({
            label: "详情",
            width: "100",
        }, ...__VLS_functionalComponentArgsRest(__VLS_98));
        const { default: __VLS_101 } = __VLS_100.slots;
        {
            const { default: __VLS_102 } = __VLS_100.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_102);
            const __VLS_103 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_104 = __VLS_asFunctionalComponent(__VLS_103, new __VLS_103({
                ...{ 'onClick': {} },
                size: "small",
            }));
            const __VLS_105 = __VLS_104({
                ...{ 'onClick': {} },
                size: "small",
            }, ...__VLS_functionalComponentArgsRest(__VLS_104));
            let __VLS_107;
            let __VLS_108;
            const __VLS_109 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.result && __VLS_ctx.task))
                            return;
                        if (!!(!__VLS_ctx.result.cleanup_analysis.length))
                            return;
                        __VLS_ctx.openJson('清理候选详情', scope.row);
                        // @ts-ignore
                        [openJson,];
                    } });
            const { default: __VLS_110 } = __VLS_106.slots;
            var __VLS_106;
        }
        var __VLS_100;
        var __VLS_66;
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
            const __VLS_111 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_112 = __VLS_asFunctionalComponent(__VLS_111, new __VLS_111({
                ...{ 'onClick': {} },
                text: true,
                type: "primary",
            }));
            const __VLS_113 = __VLS_112({
                ...{ 'onClick': {} },
                text: true,
                type: "primary",
            }, ...__VLS_functionalComponentArgsRest(__VLS_112));
            let __VLS_115;
            let __VLS_116;
            const __VLS_117 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.result && __VLS_ctx.task))
                            return;
                        if (!(__VLS_ctx.result.root_causes.length))
                            return;
                        __VLS_ctx.openJson('根因候选详情', cause);
                        // @ts-ignore
                        [openJson,];
                    } });
            const { default: __VLS_118 } = __VLS_114.slots;
            var __VLS_114;
            __VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({});
            (Math.round(cause.confidence * 100));
        }
    }
    else {
        const __VLS_119 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        ElEmpty;
        // @ts-ignore
        const __VLS_120 = __VLS_asFunctionalComponent(__VLS_119, new __VLS_119({
            description: "当前证据不足以生成根因候选。",
        }));
        const __VLS_121 = __VLS_120({
            description: "当前证据不足以生成根因候选。",
        }, ...__VLS_functionalComponentArgsRest(__VLS_120));
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
    const __VLS_124 = {}.ElTimeline;
    /** @type {[typeof __VLS_components.ElTimeline, typeof __VLS_components.elTimeline, typeof __VLS_components.ElTimeline, typeof __VLS_components.elTimeline, ]} */ ;
    // @ts-ignore
    ElTimeline;
    // @ts-ignore
    const __VLS_125 = __VLS_asFunctionalComponent(__VLS_124, new __VLS_124({
        ...{ class: "decision-timeline" },
    }));
    const __VLS_126 = __VLS_125({
        ...{ class: "decision-timeline" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_125));
    const { default: __VLS_128 } = __VLS_127.slots;
    for (const [item] of __VLS_getVForSourceType((__VLS_ctx.result.decision_chain))) {
        // @ts-ignore
        [result,];
        const __VLS_129 = {}.ElTimelineItem;
        /** @type {[typeof __VLS_components.ElTimelineItem, typeof __VLS_components.elTimelineItem, typeof __VLS_components.ElTimelineItem, typeof __VLS_components.elTimelineItem, ]} */ ;
        // @ts-ignore
        ElTimelineItem;
        // @ts-ignore
        const __VLS_130 = __VLS_asFunctionalComponent(__VLS_129, new __VLS_129({
            key: (item.stage),
            type: (item.reason_code === 'FORBIDDEN_INPUT' ? 'danger' : 'primary'),
        }));
        const __VLS_131 = __VLS_130({
            key: (item.stage),
            type: (item.reason_code === 'FORBIDDEN_INPUT' ? 'danger' : 'primary'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_130));
        const { default: __VLS_133 } = __VLS_132.slots;
        __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
        (item.stage);
        __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
        (item.summary);
        __VLS_asFunctionalElement(__VLS_elements.code, __VLS_elements.code)({});
        (item.reason_code);
        var __VLS_132;
    }
    var __VLS_127;
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    const __VLS_134 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    ElTable;
    // @ts-ignore
    const __VLS_135 = __VLS_asFunctionalComponent(__VLS_134, new __VLS_134({
        data: (__VLS_ctx.result.normalized_evidence),
        maxHeight: "420",
        emptyText: "暂无标准化证据",
    }));
    const __VLS_136 = __VLS_135({
        data: (__VLS_ctx.result.normalized_evidence),
        maxHeight: "420",
        emptyText: "暂无标准化证据",
    }, ...__VLS_functionalComponentArgsRest(__VLS_135));
    const { default: __VLS_138 } = __VLS_137.slots;
    // @ts-ignore
    [result,];
    const __VLS_139 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_140 = __VLS_asFunctionalComponent(__VLS_139, new __VLS_139({
        prop: "evidence_type",
        label: "类型",
        width: "110",
    }));
    const __VLS_141 = __VLS_140({
        prop: "evidence_type",
        label: "类型",
        width: "110",
    }, ...__VLS_functionalComponentArgsRest(__VLS_140));
    const __VLS_144 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_145 = __VLS_asFunctionalComponent(__VLS_144, new __VLS_144({
        prop: "source",
        label: "数据来源",
        width: "180",
    }));
    const __VLS_146 = __VLS_145({
        prop: "source",
        label: "数据来源",
        width: "180",
    }, ...__VLS_functionalComponentArgsRest(__VLS_145));
    const __VLS_149 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_150 = __VLS_asFunctionalComponent(__VLS_149, new __VLS_149({
        prop: "title",
        label: "证据",
    }));
    const __VLS_151 = __VLS_150({
        prop: "title",
        label: "证据",
    }, ...__VLS_functionalComponentArgsRest(__VLS_150));
    const __VLS_154 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_155 = __VLS_asFunctionalComponent(__VLS_154, new __VLS_154({
        prop: "value",
        label: "值",
    }));
    const __VLS_156 = __VLS_155({
        prop: "value",
        label: "值",
    }, ...__VLS_functionalComponentArgsRest(__VLS_155));
    const __VLS_159 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_160 = __VLS_asFunctionalComponent(__VLS_159, new __VLS_159({
        label: "异常度",
        width: "110",
    }));
    const __VLS_161 = __VLS_160({
        label: "异常度",
        width: "110",
    }, ...__VLS_functionalComponentArgsRest(__VLS_160));
    const { default: __VLS_163 } = __VLS_162.slots;
    {
        const { default: __VLS_164 } = __VLS_162.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_164);
        (Math.round(scope.row.anomaly_score * 100));
    }
    var __VLS_162;
    const __VLS_165 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_166 = __VLS_asFunctionalComponent(__VLS_165, new __VLS_165({
        prop: "trust_label",
        label: "信任标记",
        width: "160",
    }));
    const __VLS_167 = __VLS_166({
        prop: "trust_label",
        label: "信任标记",
        width: "160",
    }, ...__VLS_functionalComponentArgsRest(__VLS_166));
    const __VLS_170 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_171 = __VLS_asFunctionalComponent(__VLS_170, new __VLS_170({
        label: "详情",
        width: "100",
    }));
    const __VLS_172 = __VLS_171({
        label: "详情",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_171));
    const { default: __VLS_174 } = __VLS_173.slots;
    {
        const { default: __VLS_175 } = __VLS_173.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_175);
        const __VLS_176 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_177 = __VLS_asFunctionalComponent(__VLS_176, new __VLS_176({
            ...{ 'onClick': {} },
            size: "small",
        }));
        const __VLS_178 = __VLS_177({
            ...{ 'onClick': {} },
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_177));
        let __VLS_180;
        let __VLS_181;
        const __VLS_182 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(__VLS_ctx.result && __VLS_ctx.task))
                        return;
                    __VLS_ctx.openJson('标准化证据详情', scope.row);
                    // @ts-ignore
                    [openJson,];
                } });
        const { default: __VLS_183 } = __VLS_179.slots;
        var __VLS_179;
    }
    var __VLS_173;
    var __VLS_137;
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    const __VLS_184 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    ElTable;
    // @ts-ignore
    const __VLS_185 = __VLS_asFunctionalComponent(__VLS_184, new __VLS_184({
        data: (__VLS_ctx.result.evidence),
        emptyText: "未调用工具",
    }));
    const __VLS_186 = __VLS_185({
        data: (__VLS_ctx.result.evidence),
        emptyText: "未调用工具",
    }, ...__VLS_functionalComponentArgsRest(__VLS_185));
    const { default: __VLS_188 } = __VLS_187.slots;
    // @ts-ignore
    [result,];
    const __VLS_189 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_190 = __VLS_asFunctionalComponent(__VLS_189, new __VLS_189({
        label: "工具",
        width: "210",
    }));
    const __VLS_191 = __VLS_190({
        label: "工具",
        width: "210",
    }, ...__VLS_functionalComponentArgsRest(__VLS_190));
    const { default: __VLS_193 } = __VLS_192.slots;
    {
        const { default: __VLS_194 } = __VLS_192.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_194);
        (__VLS_ctx.toolTitle(scope.row.tool_name));
        // @ts-ignore
        [toolTitle,];
    }
    var __VLS_192;
    const __VLS_195 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_196 = __VLS_asFunctionalComponent(__VLS_195, new __VLS_195({
        prop: "trust_label",
        label: "信任标记",
        width: "180",
    }));
    const __VLS_197 = __VLS_196({
        prop: "trust_label",
        label: "信任标记",
        width: "180",
    }, ...__VLS_functionalComponentArgsRest(__VLS_196));
    const __VLS_200 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_201 = __VLS_asFunctionalComponent(__VLS_200, new __VLS_200({
        label: "注入风险",
        width: "110",
    }));
    const __VLS_202 = __VLS_201({
        label: "注入风险",
        width: "110",
    }, ...__VLS_functionalComponentArgsRest(__VLS_201));
    const { default: __VLS_204 } = __VLS_203.slots;
    {
        const { default: __VLS_205 } = __VLS_203.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_205);
        const __VLS_206 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        ElTag;
        // @ts-ignore
        const __VLS_207 = __VLS_asFunctionalComponent(__VLS_206, new __VLS_206({
            type: (scope.row.injection_suspected ? 'danger' : 'success'),
        }));
        const __VLS_208 = __VLS_207({
            type: (scope.row.injection_suspected ? 'danger' : 'success'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_207));
        const { default: __VLS_210 } = __VLS_209.slots;
        (scope.row.injection_suspected ? "疑似" : "未发现");
        var __VLS_209;
    }
    var __VLS_203;
    const __VLS_211 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_212 = __VLS_asFunctionalComponent(__VLS_211, new __VLS_211({
        label: "回执",
        width: "100",
    }));
    const __VLS_213 = __VLS_212({
        label: "回执",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_212));
    const { default: __VLS_215 } = __VLS_214.slots;
    {
        const { default: __VLS_216 } = __VLS_214.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_216);
        const __VLS_217 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_218 = __VLS_asFunctionalComponent(__VLS_217, new __VLS_217({
            ...{ 'onClick': {} },
            size: "small",
        }));
        const __VLS_219 = __VLS_218({
            ...{ 'onClick': {} },
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_218));
        let __VLS_221;
        let __VLS_222;
        const __VLS_223 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(__VLS_ctx.result && __VLS_ctx.task))
                        return;
                    __VLS_ctx.openJson('原始工具回执', scope.row.payload);
                    // @ts-ignore
                    [openJson,];
                } });
        const { default: __VLS_224 } = __VLS_220.slots;
        var __VLS_220;
    }
    var __VLS_214;
    var __VLS_187;
}
const __VLS_225 = {}.ElDrawer;
/** @type {[typeof __VLS_components.ElDrawer, typeof __VLS_components.elDrawer, typeof __VLS_components.ElDrawer, typeof __VLS_components.elDrawer, ]} */ ;
// @ts-ignore
ElDrawer;
// @ts-ignore
const __VLS_226 = __VLS_asFunctionalComponent(__VLS_225, new __VLS_225({
    modelValue: (__VLS_ctx.detailVisible),
    title: (__VLS_ctx.detailTitle),
    size: "46%",
}));
const __VLS_227 = __VLS_226({
    modelValue: (__VLS_ctx.detailVisible),
    title: (__VLS_ctx.detailTitle),
    size: "46%",
}, ...__VLS_functionalComponentArgsRest(__VLS_226));
const { default: __VLS_229 } = __VLS_228.slots;
// @ts-ignore
[detailVisible, detailTitle,];
__VLS_asFunctionalElement(__VLS_elements.pre, __VLS_elements.pre)({});
(__VLS_ctx.detailJson);
// @ts-ignore
[detailJson,];
var __VLS_228;
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
        error: error,
        loading: loading,
        detailVisible: detailVisible,
        detailTitle: detailTitle,
        detailJson: detailJson,
        run: run,
        openJson: openJson,
        formatBytes: formatBytes,
        formatArgs: formatArgs,
        tagType: tagType,
        levelText: levelText,
        intentText: intentText,
        toolTitle: toolTitle,
        causeTitle: causeTitle,
        reasonText: reasonText,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
