import { ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { useSession } from "../stores/session";
import { zhStatus } from "../status";
const session = useSession();
const examples = ["分析磁盘空间不足的原因，并列出安全清理候选", "检查 nginx 服务为什么异常", "查找僵尸进程并分析父进程", "检查 8080 端口由哪个进程占用"];
const goal = ref("");
const task = ref();
const result = ref();
const approvals = ref([]);
const error = ref("");
const loading = ref(false);
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
    if (!task.value)
        return;
    const argumentsValue = { candidate_id: candidate.candidate_id };
    try {
        await api("/executions/dry-run", { method: "POST", body: JSON.stringify({ tool_name: "safe_log_cleanup", arguments: argumentsValue }) });
        await api(`/tasks/${task.value.id}/approvals`, { method: "POST", body: JSON.stringify({ tool_name: "safe_log_cleanup", arguments: argumentsValue }) });
        ElMessage.success("审批申请已创建，请使用独立审批账号处理");
        await loadApprovals();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "审批申请失败";
    }
}
async function loadApprovals() { if (task.value)
    approvals.value = await api(`/tasks/${task.value.id}/approvals`); }
async function executeApproved(approval) {
    if (!task.value)
        return;
    try {
        const claimed = await api(`/approvals/${approval.id}/claim`, { method: "POST" });
        const argumentsValue = approval.arguments_summary.candidate_id ? { candidate_id: approval.arguments_summary.candidate_id } : approval.arguments_summary;
        const execution = await api("/executions/run", { method: "POST", body: JSON.stringify({ task_id: task.value.id, tool_name: approval.tool_name, arguments: argumentsValue, approval_token: claimed.approval_token }) });
        ElMessage.success(`执行完成：${execution.verification}`);
        await loadApprovals();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "受控执行失败";
    }
}
function formatBytes(value) { if (value === undefined)
    return "—"; const units = ["B", "KB", "MB", "GB", "TB"]; let size = value, index = 0; while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index++;
} return `${size.toFixed(index ? 1 : 0)} ${units[index]}`; }
function intentText(value) { return { QUERY: "查询", DIAGNOSIS: "故障诊断", INSPECTION: "安全巡检", CHANGE: "受控变更", CLEANUP: "清理分析", RECOVERY: "恢复", FORBIDDEN: "禁止请求" }[value] || value; }
function causeTitle(value) { return { disk_pressure: "磁盘空间压力", high_cpu: "CPU 负载异常", zombie_process: "僵尸进程", service_failure: "服务故障", config_drift: "配置漂移" }[value] || value; }
function reasonText(value) { return { SAFE_CANDIDATE: "满足安全候选规则", FILE_IS_OPEN: "文件正在使用", OPEN_FILE_STATE_UNKNOWN: "无法确认文件占用状态", CRITICAL_OR_DATABASE_LOG: "关键或数据库日志", RETENTION_PERIOD_NOT_MET: "未达到保留期限", FILE_TYPE_NOT_ALLOWED: "文件类型不允许", BELOW_SIZE_THRESHOLD: "未达到清理阈值", PROTECTED_PATH: "受保护路径" }[value] || value; }
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
    placeholder: "例如：分析磁盘空间不足的原因，并列出可以安全清理的旧日志，不要自动删除",
}));
const __VLS_2 = __VLS_1({
    ...{ 'onKeydown': {} },
    modelValue: (__VLS_ctx.goal),
    type: "textarea",
    rows: (5),
    maxlength: "4000",
    showWordLimit: true,
    placeholder: "例如：分析磁盘空间不足的原因，并列出可以安全清理的旧日志，不要自动删除",
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
    const __VLS_21 = {}.ElTimeline;
    /** @type {[typeof __VLS_components.ElTimeline, typeof __VLS_components.elTimeline, typeof __VLS_components.ElTimeline, typeof __VLS_components.elTimeline, ]} */ ;
    // @ts-ignore
    ElTimeline;
    // @ts-ignore
    const __VLS_22 = __VLS_asFunctionalComponent(__VLS_21, new __VLS_21({
        ...{ class: "decision-timeline" },
    }));
    const __VLS_23 = __VLS_22({
        ...{ class: "decision-timeline" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_22));
    const { default: __VLS_25 } = __VLS_24.slots;
    for (const [item] of __VLS_getVForSourceType((__VLS_ctx.result.decision_chain))) {
        // @ts-ignore
        [result,];
        const __VLS_26 = {}.ElTimelineItem;
        /** @type {[typeof __VLS_components.ElTimelineItem, typeof __VLS_components.elTimelineItem, typeof __VLS_components.ElTimelineItem, typeof __VLS_components.elTimelineItem, ]} */ ;
        // @ts-ignore
        ElTimelineItem;
        // @ts-ignore
        const __VLS_27 = __VLS_asFunctionalComponent(__VLS_26, new __VLS_26({
            key: (item.stage),
            type: (item.reason_code === 'FORBIDDEN_INPUT' ? 'danger' : 'primary'),
        }));
        const __VLS_28 = __VLS_27({
            key: (item.stage),
            type: (item.reason_code === 'FORBIDDEN_INPUT' ? 'danger' : 'primary'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_27));
        const { default: __VLS_30 } = __VLS_29.slots;
        __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({});
        (item.stage);
        __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
        (item.summary);
        __VLS_asFunctionalElement(__VLS_elements.code, __VLS_elements.code)({});
        (item.reason_code);
        var __VLS_29;
    }
    var __VLS_24;
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
            (cause.recommended_actions.join('；'));
            __VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({});
            (Math.round(cause.confidence * 100));
        }
    }
    else {
        const __VLS_31 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        ElEmpty;
        // @ts-ignore
        const __VLS_32 = __VLS_asFunctionalComponent(__VLS_31, new __VLS_31({
            description: "当前证据不足以生成根因候选",
        }));
        const __VLS_33 = __VLS_32({
            description: "当前证据不足以生成根因候选",
        }, ...__VLS_functionalComponentArgsRest(__VLS_32));
    }
    __VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
        ...{ class: "panel candidate-panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "panel-head" },
    });
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
    __VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    const __VLS_36 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    ElTag;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        type: (__VLS_ctx.session.mode === 'CONTROLLED_EXECUTION' ? 'warning' : 'info'),
    }));
    const __VLS_38 = __VLS_37({
        type: (__VLS_ctx.session.mode === 'CONTROLLED_EXECUTION' ? 'warning' : 'info'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    const { default: __VLS_40 } = __VLS_39.slots;
    // @ts-ignore
    [session,];
    (__VLS_ctx.session.mode === 'CONTROLLED_EXECUTION' ? '可申请受控执行' : '仅分析，不会删除');
    // @ts-ignore
    [session,];
    var __VLS_39;
    const __VLS_41 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    ElTable;
    // @ts-ignore
    const __VLS_42 = __VLS_asFunctionalComponent(__VLS_41, new __VLS_41({
        data: (__VLS_ctx.result.cleanup_analysis),
        emptyText: "未发现满足安全规则的清理候选",
    }));
    const __VLS_43 = __VLS_42({
        data: (__VLS_ctx.result.cleanup_analysis),
        emptyText: "未发现满足安全规则的清理候选",
    }, ...__VLS_functionalComponentArgsRest(__VLS_42));
    const { default: __VLS_45 } = __VLS_44.slots;
    // @ts-ignore
    [result,];
    const __VLS_46 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_47 = __VLS_asFunctionalComponent(__VLS_46, new __VLS_46({
        label: "判定",
        width: "100",
    }));
    const __VLS_48 = __VLS_47({
        label: "判定",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_47));
    const { default: __VLS_50 } = __VLS_49.slots;
    {
        const { default: __VLS_51 } = __VLS_49.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_51);
        const __VLS_52 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        ElTag;
        // @ts-ignore
        const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
            type: (scope.row.eligible ? 'success' : 'danger'),
        }));
        const __VLS_54 = __VLS_53({
            type: (scope.row.eligible ? 'success' : 'danger'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_53));
        const { default: __VLS_56 } = __VLS_55.slots;
        (scope.row.eligible ? '可申请' : '已排除');
        var __VLS_55;
    }
    var __VLS_49;
    const __VLS_57 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_58 = __VLS_asFunctionalComponent(__VLS_57, new __VLS_57({
        label: "文件",
    }));
    const __VLS_59 = __VLS_58({
        label: "文件",
    }, ...__VLS_functionalComponentArgsRest(__VLS_58));
    const { default: __VLS_61 } = __VLS_60.slots;
    {
        const { default: __VLS_62 } = __VLS_60.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_62);
        (scope.row.candidate?.path || '—');
    }
    var __VLS_60;
    const __VLS_63 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_64 = __VLS_asFunctionalComponent(__VLS_63, new __VLS_63({
        label: "大小",
        width: "130",
    }));
    const __VLS_65 = __VLS_64({
        label: "大小",
        width: "130",
    }, ...__VLS_functionalComponentArgsRest(__VLS_64));
    const { default: __VLS_67 } = __VLS_66.slots;
    {
        const { default: __VLS_68 } = __VLS_66.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_68);
        (__VLS_ctx.formatBytes(scope.row.candidate?.size_bytes));
        // @ts-ignore
        [formatBytes,];
    }
    var __VLS_66;
    const __VLS_69 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_70 = __VLS_asFunctionalComponent(__VLS_69, new __VLS_69({
        label: "规则结果",
        minWidth: "230",
    }));
    const __VLS_71 = __VLS_70({
        label: "规则结果",
        minWidth: "230",
    }, ...__VLS_functionalComponentArgsRest(__VLS_70));
    const { default: __VLS_73 } = __VLS_72.slots;
    {
        const { default: __VLS_74 } = __VLS_72.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_74);
        (scope.row.reason_codes.map(__VLS_ctx.reasonText).join('；'));
        // @ts-ignore
        [reasonText,];
    }
    var __VLS_72;
    const __VLS_75 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_76 = __VLS_asFunctionalComponent(__VLS_75, new __VLS_75({
        label: "操作",
        width: "150",
    }));
    const __VLS_77 = __VLS_76({
        label: "操作",
        width: "150",
    }, ...__VLS_functionalComponentArgsRest(__VLS_76));
    const { default: __VLS_79 } = __VLS_78.slots;
    {
        const { default: __VLS_80 } = __VLS_78.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_80);
        if (scope.row.eligible && __VLS_ctx.session.mode === 'CONTROLLED_EXECUTION') {
            // @ts-ignore
            [session,];
            const __VLS_81 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_82 = __VLS_asFunctionalComponent(__VLS_81, new __VLS_81({
                ...{ 'onClick': {} },
                type: "warning",
                size: "small",
            }));
            const __VLS_83 = __VLS_82({
                ...{ 'onClick': {} },
                type: "warning",
                size: "small",
            }, ...__VLS_functionalComponentArgsRest(__VLS_82));
            let __VLS_85;
            let __VLS_86;
            const __VLS_87 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.result && __VLS_ctx.task))
                            return;
                        if (!(scope.row.eligible && __VLS_ctx.session.mode === 'CONTROLLED_EXECUTION'))
                            return;
                        __VLS_ctx.requestCleanup(scope.row.candidate);
                        // @ts-ignore
                        [requestCleanup,];
                    } });
            const { default: __VLS_88 } = __VLS_84.slots;
            var __VLS_84;
        }
        else {
            __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
        }
    }
    var __VLS_78;
    var __VLS_44;
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
        const __VLS_89 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_90 = __VLS_asFunctionalComponent(__VLS_89, new __VLS_89({
            ...{ 'onClick': {} },
        }));
        const __VLS_91 = __VLS_90({
            ...{ 'onClick': {} },
        }, ...__VLS_functionalComponentArgsRest(__VLS_90));
        let __VLS_93;
        let __VLS_94;
        const __VLS_95 = ({ click: {} },
            { onClick: (__VLS_ctx.loadApprovals) });
        const { default: __VLS_96 } = __VLS_92.slots;
        // @ts-ignore
        [loadApprovals,];
        var __VLS_92;
        const __VLS_97 = {}.ElTable;
        /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
        // @ts-ignore
        ElTable;
        // @ts-ignore
        const __VLS_98 = __VLS_asFunctionalComponent(__VLS_97, new __VLS_97({
            data: (__VLS_ctx.approvals),
        }));
        const __VLS_99 = __VLS_98({
            data: (__VLS_ctx.approvals),
        }, ...__VLS_functionalComponentArgsRest(__VLS_98));
        const { default: __VLS_101 } = __VLS_100.slots;
        // @ts-ignore
        [approvals,];
        const __VLS_102 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_103 = __VLS_asFunctionalComponent(__VLS_102, new __VLS_102({
            prop: "tool_name",
            label: "受控工具",
        }));
        const __VLS_104 = __VLS_103({
            prop: "tool_name",
            label: "受控工具",
        }, ...__VLS_functionalComponentArgsRest(__VLS_103));
        const __VLS_107 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_108 = __VLS_asFunctionalComponent(__VLS_107, new __VLS_107({
            label: "目标",
        }));
        const __VLS_109 = __VLS_108({
            label: "目标",
        }, ...__VLS_functionalComponentArgsRest(__VLS_108));
        const { default: __VLS_111 } = __VLS_110.slots;
        {
            const { default: __VLS_112 } = __VLS_110.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_112);
            (scope.row.arguments_summary.candidate_id || scope.row.arguments_summary.service || scope.row.arguments_summary.target_id || scope.row.arguments_summary.change_id);
        }
        var __VLS_110;
        const __VLS_113 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_114 = __VLS_asFunctionalComponent(__VLS_113, new __VLS_113({
            label: "状态",
            width: "110",
        }));
        const __VLS_115 = __VLS_114({
            label: "状态",
            width: "110",
        }, ...__VLS_functionalComponentArgsRest(__VLS_114));
        const { default: __VLS_117 } = __VLS_116.slots;
        {
            const { default: __VLS_118 } = __VLS_116.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_118);
            (__VLS_ctx.zhStatus(scope.row.status));
            // @ts-ignore
            [zhStatus,];
        }
        var __VLS_116;
        const __VLS_119 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_120 = __VLS_asFunctionalComponent(__VLS_119, new __VLS_119({
            label: "操作",
            width: "160",
        }));
        const __VLS_121 = __VLS_120({
            label: "操作",
            width: "160",
        }, ...__VLS_functionalComponentArgsRest(__VLS_120));
        const { default: __VLS_123 } = __VLS_122.slots;
        {
            const { default: __VLS_124 } = __VLS_122.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_124);
            if (scope.row.status === 'APPROVED') {
                const __VLS_125 = {}.ElButton;
                /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
                // @ts-ignore
                ElButton;
                // @ts-ignore
                const __VLS_126 = __VLS_asFunctionalComponent(__VLS_125, new __VLS_125({
                    ...{ 'onClick': {} },
                    type: "success",
                    size: "small",
                }));
                const __VLS_127 = __VLS_126({
                    ...{ 'onClick': {} },
                    type: "success",
                    size: "small",
                }, ...__VLS_functionalComponentArgsRest(__VLS_126));
                let __VLS_129;
                let __VLS_130;
                const __VLS_131 = ({ click: {} },
                    { onClick: (...[$event]) => {
                            if (!(__VLS_ctx.result && __VLS_ctx.task))
                                return;
                            if (!(__VLS_ctx.approvals.length))
                                return;
                            if (!(scope.row.status === 'APPROVED'))
                                return;
                            __VLS_ctx.executeApproved(scope.row);
                            // @ts-ignore
                            [executeApproved,];
                        } });
                const { default: __VLS_132 } = __VLS_128.slots;
                var __VLS_128;
            }
            else if (scope.row.status === 'PENDING') {
                __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
            }
            else {
                __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
            }
        }
        var __VLS_122;
        var __VLS_100;
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
    const __VLS_133 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    ElTable;
    // @ts-ignore
    const __VLS_134 = __VLS_asFunctionalComponent(__VLS_133, new __VLS_133({
        data: (__VLS_ctx.result.normalized_evidence),
        maxHeight: "420",
    }));
    const __VLS_135 = __VLS_134({
        data: (__VLS_ctx.result.normalized_evidence),
        maxHeight: "420",
    }, ...__VLS_functionalComponentArgsRest(__VLS_134));
    const { default: __VLS_137 } = __VLS_136.slots;
    // @ts-ignore
    [result,];
    const __VLS_138 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_139 = __VLS_asFunctionalComponent(__VLS_138, new __VLS_138({
        prop: "evidence_type",
        label: "类型",
        width: "110",
    }));
    const __VLS_140 = __VLS_139({
        prop: "evidence_type",
        label: "类型",
        width: "110",
    }, ...__VLS_functionalComponentArgsRest(__VLS_139));
    const __VLS_143 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_144 = __VLS_asFunctionalComponent(__VLS_143, new __VLS_143({
        prop: "source",
        label: "数据来源",
        width: "170",
    }));
    const __VLS_145 = __VLS_144({
        prop: "source",
        label: "数据来源",
        width: "170",
    }, ...__VLS_functionalComponentArgsRest(__VLS_144));
    const __VLS_148 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_149 = __VLS_asFunctionalComponent(__VLS_148, new __VLS_148({
        prop: "title",
        label: "证据",
    }));
    const __VLS_150 = __VLS_149({
        prop: "title",
        label: "证据",
    }, ...__VLS_functionalComponentArgsRest(__VLS_149));
    const __VLS_153 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_154 = __VLS_asFunctionalComponent(__VLS_153, new __VLS_153({
        prop: "value",
        label: "值",
    }));
    const __VLS_155 = __VLS_154({
        prop: "value",
        label: "值",
    }, ...__VLS_functionalComponentArgsRest(__VLS_154));
    const __VLS_158 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_159 = __VLS_asFunctionalComponent(__VLS_158, new __VLS_158({
        label: "异常度",
        width: "100",
    }));
    const __VLS_160 = __VLS_159({
        label: "异常度",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_159));
    const { default: __VLS_162 } = __VLS_161.slots;
    {
        const { default: __VLS_163 } = __VLS_161.slots;
        const [scope] = __VLS_getSlotParameters(__VLS_163);
        (Math.round(scope.row.anomaly_score * 100));
    }
    var __VLS_161;
    const __VLS_164 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    ElTableColumn;
    // @ts-ignore
    const __VLS_165 = __VLS_asFunctionalComponent(__VLS_164, new __VLS_164({
        prop: "trust_label",
        label: "信任标记",
        width: "150",
    }));
    const __VLS_166 = __VLS_165({
        prop: "trust_label",
        label: "信任标记",
        width: "150",
    }, ...__VLS_functionalComponentArgsRest(__VLS_165));
    var __VLS_136;
}
/** @type {__VLS_StyleScopedClasses['task-page']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['task-composer']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['mode-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['prompt-examples']} */ ;
/** @type {__VLS_StyleScopedClasses['composer-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['task-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['result-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['risk-level']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['task-columns']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['decision-timeline']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['rca-list']} */ ;
/** @type {__VLS_StyleScopedClasses['rca-card']} */ ;
/** @type {__VLS_StyleScopedClasses['rank']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['candidate-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
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
        run: run,
        requestCleanup: requestCleanup,
        loadApprovals: loadApprovals,
        executeApproved: executeApproved,
        formatBytes: formatBytes,
        intentText: intentText,
        causeTitle: causeTitle,
        reasonText: reasonText,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
