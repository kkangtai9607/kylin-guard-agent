import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { zhStatus } from "../status";
const capabilities = reactive({ enabled: false, mode: "READ_ONLY", allowed_services: [], managed_configs: [], managed_processes: [] });
const tool = ref("service_restart");
const service = ref("nginx");
const targetId = ref("nginx-main");
const content = ref("");
const pid = ref(2);
const preview = ref();
const error = ref("");
const submitting = ref(false);
const approvals = ref([]);
const executions = ref([]);
const taskIds = ref([]);
const actionArguments = reactive({});
async function loadCapabilities() {
    Object.assign(capabilities, await api("/controlled/capabilities"));
    service.value = capabilities.allowed_services[0] || "";
    targetId.value = capabilities.managed_configs[0]?.target_id || "";
}
async function prepare() {
    submitting.value = true;
    error.value = "";
    try {
        const task = await api("/tasks", { method: "POST", body: JSON.stringify({ goal: goalText(), requested_mode: "CONTROLLED_EXECUTION" }) });
        taskIds.value.push(task.id);
        let args;
        if (tool.value === "service_restart")
            args = { service: service.value };
        else if (tool.value === "config_safe_update")
            args = { target_id: targetId.value, content: content.value };
        else {
            const candidate = await api("/process-candidates", { method: "POST", body: JSON.stringify({ task_id: task.id, pid: pid.value }) });
            args = { candidate_id: candidate.candidate_id };
        }
        preview.value = await api("/executions/dry-run", { method: "POST", body: JSON.stringify({ tool_name: tool.value, arguments: args }) });
        const approval = await api(`/tasks/${task.id}/approvals`, { method: "POST", body: JSON.stringify({ tool_name: tool.value, arguments: args }) });
        actionArguments[approval.id] = args;
        ElMessage.success("风险确认已创建");
        await refreshApprovals();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "操作准备失败";
    }
    finally {
        submitting.value = false;
    }
}
async function refreshApprovals() {
    const collected = [];
    for (const taskId of taskIds.value)
        collected.push(...await api(`/tasks/${taskId}/approvals`));
    approvals.value = collected;
}
async function execute(approval) {
    try {
        const claimed = await api(`/approvals/${approval.id}/claim`, { method: "POST" });
        const args = actionArguments[approval.id] || approval.arguments_summary;
        await api("/executions/run", { method: "POST", body: JSON.stringify({ task_id: approval.task_id, tool_name: approval.tool_name, arguments: args, approval_token: claimed.approval_token }) });
        delete actionArguments[approval.id];
        ElMessage.success("执行与验证完成");
        await refreshApprovals();
        await loadExecutions();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "执行失败";
    }
}
async function requestRollback(execution) {
    try {
        const args = { change_id: execution.change_id };
        const approval = await api(`/tasks/${execution.task_id}/approvals`, { method: "POST", body: JSON.stringify({ tool_name: "rollback_change", arguments: args }) });
        if (!taskIds.value.includes(execution.task_id))
            taskIds.value.push(execution.task_id);
        actionArguments[approval.id] = args;
        ElMessage.success("回滚风险确认已创建");
        await refreshApprovals();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "回滚申请失败";
    }
}
async function loadExecutions() {
    executions.value = await api("/executions");
}
function goalText() {
    if (tool.value === "service_restart")
        return `重启白名单服务 ${service.value}`;
    if (tool.value === "config_safe_update")
        return `安全更新托管配置 ${targetId.value}`;
    return `终止受控托管进程 PID ${pid.value}`;
}
function argumentText(value) {
    return Object.entries(value).map(([key, item]) => `${key}=${item}`).join(" · ");
}
function toolText(value) {
    return { safe_log_cleanup: "清理候选文件", service_restart: "重启服务", config_safe_update: "更新配置", terminate_process: "终止进程", rollback_change: "回滚变更" }[value] || value;
}
onMounted(async () => {
    try {
        await loadCapabilities();
        await loadExecutions();
    }
    catch (e) {
        error.value = e instanceof Error ? e.message : "页面加载失败";
    }
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_elements;
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "controlled-page" },
});
if (!__VLS_ctx.capabilities.enabled) {
    // @ts-ignore
    [capabilities,];
    const __VLS_0 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    ElAlert;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
        title: "当前处于诊断模式",
        description: "可以查看操作流程和历史记录；涉及删除、重启、修改配置等写操作时，需要先由部署配置启用运维执行模式。",
        type: "info",
        showIcon: true,
    }));
    const __VLS_2 = __VLS_1({
        title: "当前处于诊断模式",
        description: "可以查看操作流程和历史记录；涉及删除、重启、修改配置等写操作时，需要先由部署配置启用运维执行模式。",
        type: "info",
        showIcon: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
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
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({
    ...{ class: "mode-badge" },
});
(__VLS_ctx.zhStatus(__VLS_ctx.capabilities.mode));
// @ts-ignore
[capabilities, zhStatus,];
const __VLS_5 = {}.ElTabs;
/** @type {[typeof __VLS_components.ElTabs, typeof __VLS_components.elTabs, typeof __VLS_components.ElTabs, typeof __VLS_components.elTabs, ]} */ ;
// @ts-ignore
ElTabs;
// @ts-ignore
const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
    modelValue: (__VLS_ctx.tool),
}));
const __VLS_7 = __VLS_6({
    modelValue: (__VLS_ctx.tool),
}, ...__VLS_functionalComponentArgsRest(__VLS_6));
const { default: __VLS_9 } = __VLS_8.slots;
// @ts-ignore
[tool,];
const __VLS_10 = {}.ElTabPane;
/** @type {[typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, ]} */ ;
// @ts-ignore
ElTabPane;
// @ts-ignore
const __VLS_11 = __VLS_asFunctionalComponent(__VLS_10, new __VLS_10({
    label: "重启白名单服务",
    name: "service_restart",
}));
const __VLS_12 = __VLS_11({
    label: "重启白名单服务",
    name: "service_restart",
}, ...__VLS_functionalComponentArgsRest(__VLS_11));
const __VLS_15 = {}.ElTabPane;
/** @type {[typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, ]} */ ;
// @ts-ignore
ElTabPane;
// @ts-ignore
const __VLS_16 = __VLS_asFunctionalComponent(__VLS_15, new __VLS_15({
    label: "安全更新配置",
    name: "config_safe_update",
}));
const __VLS_17 = __VLS_16({
    label: "安全更新配置",
    name: "config_safe_update",
}, ...__VLS_functionalComponentArgsRest(__VLS_16));
const __VLS_20 = {}.ElTabPane;
/** @type {[typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, ]} */ ;
// @ts-ignore
ElTabPane;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    label: "终止托管进程",
    name: "terminate_process",
}));
const __VLS_22 = __VLS_21({
    label: "终止托管进程",
    name: "terminate_process",
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
var __VLS_8;
const __VLS_25 = {}.ElForm;
/** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
// @ts-ignore
ElForm;
// @ts-ignore
const __VLS_26 = __VLS_asFunctionalComponent(__VLS_25, new __VLS_25({
    labelPosition: "top",
    ...{ class: "controlled-form" },
}));
const __VLS_27 = __VLS_26({
    labelPosition: "top",
    ...{ class: "controlled-form" },
}, ...__VLS_functionalComponentArgsRest(__VLS_26));
const { default: __VLS_29 } = __VLS_28.slots;
if (__VLS_ctx.tool === 'service_restart') {
    // @ts-ignore
    [tool,];
    const __VLS_30 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_31 = __VLS_asFunctionalComponent(__VLS_30, new __VLS_30({
        label: "白名单服务",
    }));
    const __VLS_32 = __VLS_31({
        label: "白名单服务",
    }, ...__VLS_functionalComponentArgsRest(__VLS_31));
    const { default: __VLS_34 } = __VLS_33.slots;
    const __VLS_35 = {}.ElSelect;
    /** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
    // @ts-ignore
    ElSelect;
    // @ts-ignore
    const __VLS_36 = __VLS_asFunctionalComponent(__VLS_35, new __VLS_35({
        modelValue: (__VLS_ctx.service),
    }));
    const __VLS_37 = __VLS_36({
        modelValue: (__VLS_ctx.service),
    }, ...__VLS_functionalComponentArgsRest(__VLS_36));
    const { default: __VLS_39 } = __VLS_38.slots;
    // @ts-ignore
    [service,];
    for (const [item] of __VLS_getVForSourceType((__VLS_ctx.capabilities.allowed_services))) {
        // @ts-ignore
        [capabilities,];
        const __VLS_40 = {}.ElOption;
        /** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
        // @ts-ignore
        ElOption;
        // @ts-ignore
        const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
            key: (item),
            label: (item),
            value: (item),
        }));
        const __VLS_42 = __VLS_41({
            key: (item),
            label: (item),
            value: (item),
        }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    }
    var __VLS_38;
    var __VLS_33;
}
if (__VLS_ctx.tool === 'config_safe_update') {
    // @ts-ignore
    [tool,];
    const __VLS_45 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_46 = __VLS_asFunctionalComponent(__VLS_45, new __VLS_45({
        label: "托管配置目标",
    }));
    const __VLS_47 = __VLS_46({
        label: "托管配置目标",
    }, ...__VLS_functionalComponentArgsRest(__VLS_46));
    const { default: __VLS_49 } = __VLS_48.slots;
    const __VLS_50 = {}.ElSelect;
    /** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
    // @ts-ignore
    ElSelect;
    // @ts-ignore
    const __VLS_51 = __VLS_asFunctionalComponent(__VLS_50, new __VLS_50({
        modelValue: (__VLS_ctx.targetId),
    }));
    const __VLS_52 = __VLS_51({
        modelValue: (__VLS_ctx.targetId),
    }, ...__VLS_functionalComponentArgsRest(__VLS_51));
    const { default: __VLS_54 } = __VLS_53.slots;
    // @ts-ignore
    [targetId,];
    for (const [item] of __VLS_getVForSourceType((__VLS_ctx.capabilities.managed_configs))) {
        // @ts-ignore
        [capabilities,];
        const __VLS_55 = {}.ElOption;
        /** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
        // @ts-ignore
        ElOption;
        // @ts-ignore
        const __VLS_56 = __VLS_asFunctionalComponent(__VLS_55, new __VLS_55({
            key: (item.target_id),
            label: (`${item.target_id}（${item.validator} 校验）`),
            value: (item.target_id),
        }));
        const __VLS_57 = __VLS_56({
            key: (item.target_id),
            label: (`${item.target_id}（${item.validator} 校验）`),
            value: (item.target_id),
        }, ...__VLS_functionalComponentArgsRest(__VLS_56));
    }
    var __VLS_53;
    var __VLS_48;
    const __VLS_60 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
        label: "新配置内容",
    }));
    const __VLS_62 = __VLS_61({
        label: "新配置内容",
    }, ...__VLS_functionalComponentArgsRest(__VLS_61));
    const { default: __VLS_64 } = __VLS_63.slots;
    const __VLS_65 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    ElInput;
    // @ts-ignore
    const __VLS_66 = __VLS_asFunctionalComponent(__VLS_65, new __VLS_65({
        modelValue: (__VLS_ctx.content),
        type: "textarea",
        rows: (7),
        maxlength: "1048576",
        showWordLimit: true,
    }));
    const __VLS_67 = __VLS_66({
        modelValue: (__VLS_ctx.content),
        type: "textarea",
        rows: (7),
        maxlength: "1048576",
        showWordLimit: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_66));
    // @ts-ignore
    [content,];
    var __VLS_63;
}
if (__VLS_ctx.tool === 'terminate_process') {
    // @ts-ignore
    [tool,];
    const __VLS_70 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_71 = __VLS_asFunctionalComponent(__VLS_70, new __VLS_70({
        label: "进程 PID",
    }));
    const __VLS_72 = __VLS_71({
        label: "进程 PID",
    }, ...__VLS_functionalComponentArgsRest(__VLS_71));
    const { default: __VLS_74 } = __VLS_73.slots;
    const __VLS_75 = {}.ElInputNumber;
    /** @type {[typeof __VLS_components.ElInputNumber, typeof __VLS_components.elInputNumber, ]} */ ;
    // @ts-ignore
    ElInputNumber;
    // @ts-ignore
    const __VLS_76 = __VLS_asFunctionalComponent(__VLS_75, new __VLS_75({
        modelValue: (__VLS_ctx.pid),
        min: (2),
        max: (4194304),
    }));
    const __VLS_77 = __VLS_76({
        modelValue: (__VLS_ctx.pid),
        min: (2),
        max: (4194304),
    }, ...__VLS_functionalComponentArgsRest(__VLS_76));
    // @ts-ignore
    [pid,];
    var __VLS_73;
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({
        ...{ class: "form-note" },
    });
}
const __VLS_80 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
    ...{ 'onClick': {} },
    type: "warning",
    disabled: (!__VLS_ctx.capabilities.enabled),
    loading: (__VLS_ctx.submitting),
}));
const __VLS_82 = __VLS_81({
    ...{ 'onClick': {} },
    type: "warning",
    disabled: (!__VLS_ctx.capabilities.enabled),
    loading: (__VLS_ctx.submitting),
}, ...__VLS_functionalComponentArgsRest(__VLS_81));
let __VLS_84;
let __VLS_85;
const __VLS_86 = ({ click: {} },
    { onClick: (__VLS_ctx.prepare) });
const { default: __VLS_87 } = __VLS_83.slots;
// @ts-ignore
[capabilities, submitting, prepare,];
var __VLS_83;
var __VLS_28;
if (__VLS_ctx.error) {
    // @ts-ignore
    [error,];
    const __VLS_88 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    ElAlert;
    // @ts-ignore
    const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
        title: (__VLS_ctx.error),
        type: "error",
        showIcon: true,
        closable: (false),
    }));
    const __VLS_90 = __VLS_89({
        title: (__VLS_ctx.error),
        type: "error",
        showIcon: true,
        closable: (false),
    }, ...__VLS_functionalComponentArgsRest(__VLS_89));
    // @ts-ignore
    [error,];
}
if (__VLS_ctx.preview) {
    // @ts-ignore
    [preview,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "dry-run-card" },
    });
    __VLS_asFunctionalElement(__VLS_elements.h4, __VLS_elements.h4)({});
    __VLS_asFunctionalElement(__VLS_elements.pre, __VLS_elements.pre)({});
    (JSON.stringify(__VLS_ctx.preview, null, 2));
    // @ts-ignore
    [preview,];
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
const __VLS_93 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_94 = __VLS_asFunctionalComponent(__VLS_93, new __VLS_93({
    ...{ 'onClick': {} },
}));
const __VLS_95 = __VLS_94({
    ...{ 'onClick': {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_94));
let __VLS_97;
let __VLS_98;
const __VLS_99 = ({ click: {} },
    { onClick: (__VLS_ctx.refreshApprovals) });
const { default: __VLS_100 } = __VLS_96.slots;
// @ts-ignore
[refreshApprovals,];
var __VLS_96;
const __VLS_101 = {}.ElTable;
/** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
// @ts-ignore
ElTable;
// @ts-ignore
const __VLS_102 = __VLS_asFunctionalComponent(__VLS_101, new __VLS_101({
    data: (__VLS_ctx.approvals),
    emptyText: "本页面尚未创建风险确认",
}));
const __VLS_103 = __VLS_102({
    data: (__VLS_ctx.approvals),
    emptyText: "本页面尚未创建风险确认",
}, ...__VLS_functionalComponentArgsRest(__VLS_102));
const { default: __VLS_105 } = __VLS_104.slots;
// @ts-ignore
[approvals,];
const __VLS_106 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_107 = __VLS_asFunctionalComponent(__VLS_106, new __VLS_106({
    label: "工具",
    width: "190",
}));
const __VLS_108 = __VLS_107({
    label: "工具",
    width: "190",
}, ...__VLS_functionalComponentArgsRest(__VLS_107));
const { default: __VLS_110 } = __VLS_109.slots;
{
    const { default: __VLS_111 } = __VLS_109.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_111);
    (__VLS_ctx.toolText(scope.row.tool_name));
    // @ts-ignore
    [toolText,];
}
var __VLS_109;
const __VLS_112 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_113 = __VLS_asFunctionalComponent(__VLS_112, new __VLS_112({
    label: "参数摘要",
}));
const __VLS_114 = __VLS_113({
    label: "参数摘要",
}, ...__VLS_functionalComponentArgsRest(__VLS_113));
const { default: __VLS_116 } = __VLS_115.slots;
{
    const { default: __VLS_117 } = __VLS_115.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_117);
    (__VLS_ctx.argumentText(scope.row.arguments_summary));
    // @ts-ignore
    [argumentText,];
}
var __VLS_115;
const __VLS_118 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_119 = __VLS_asFunctionalComponent(__VLS_118, new __VLS_118({
    label: "状态",
    width: "110",
}));
const __VLS_120 = __VLS_119({
    label: "状态",
    width: "110",
}, ...__VLS_functionalComponentArgsRest(__VLS_119));
const { default: __VLS_122 } = __VLS_121.slots;
{
    const { default: __VLS_123 } = __VLS_121.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_123);
    (__VLS_ctx.zhStatus(scope.row.status));
    // @ts-ignore
    [zhStatus,];
}
var __VLS_121;
const __VLS_124 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_125 = __VLS_asFunctionalComponent(__VLS_124, new __VLS_124({
    label: "操作",
    width: "180",
}));
const __VLS_126 = __VLS_125({
    label: "操作",
    width: "180",
}, ...__VLS_functionalComponentArgsRest(__VLS_125));
const { default: __VLS_128 } = __VLS_127.slots;
{
    const { default: __VLS_129 } = __VLS_127.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_129);
    if (scope.row.status === 'APPROVED') {
        const __VLS_130 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_131 = __VLS_asFunctionalComponent(__VLS_130, new __VLS_130({
            ...{ 'onClick': {} },
            type: "success",
            size: "small",
        }));
        const __VLS_132 = __VLS_131({
            ...{ 'onClick': {} },
            type: "success",
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_131));
        let __VLS_134;
        let __VLS_135;
        const __VLS_136 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(scope.row.status === 'APPROVED'))
                        return;
                    __VLS_ctx.execute(scope.row);
                    // @ts-ignore
                    [execute,];
                } });
        const { default: __VLS_137 } = __VLS_133.slots;
        var __VLS_133;
    }
    else if (scope.row.status === 'PENDING') {
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    }
    else {
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    }
}
var __VLS_127;
var __VLS_104;
__VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
    ...{ class: "panel" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel-head" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
const __VLS_138 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_139 = __VLS_asFunctionalComponent(__VLS_138, new __VLS_138({
    ...{ 'onClick': {} },
}));
const __VLS_140 = __VLS_139({
    ...{ 'onClick': {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_139));
let __VLS_142;
let __VLS_143;
const __VLS_144 = ({ click: {} },
    { onClick: (__VLS_ctx.loadExecutions) });
const { default: __VLS_145 } = __VLS_141.slots;
// @ts-ignore
[loadExecutions,];
var __VLS_141;
const __VLS_146 = {}.ElTable;
/** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
// @ts-ignore
ElTable;
// @ts-ignore
const __VLS_147 = __VLS_asFunctionalComponent(__VLS_146, new __VLS_146({
    data: (__VLS_ctx.executions),
    emptyText: "暂无执行记录",
}));
const __VLS_148 = __VLS_147({
    data: (__VLS_ctx.executions),
    emptyText: "暂无执行记录",
}, ...__VLS_functionalComponentArgsRest(__VLS_147));
const { default: __VLS_150 } = __VLS_149.slots;
// @ts-ignore
[executions,];
const __VLS_151 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_152 = __VLS_asFunctionalComponent(__VLS_151, new __VLS_151({
    label: "工具",
    width: "180",
}));
const __VLS_153 = __VLS_152({
    label: "工具",
    width: "180",
}, ...__VLS_functionalComponentArgsRest(__VLS_152));
const { default: __VLS_155 } = __VLS_154.slots;
{
    const { default: __VLS_156 } = __VLS_154.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_156);
    (__VLS_ctx.toolText(scope.row.tool_name));
    // @ts-ignore
    [toolText,];
}
var __VLS_154;
const __VLS_157 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_158 = __VLS_asFunctionalComponent(__VLS_157, new __VLS_157({
    prop: "target_ref",
    label: "目标",
}));
const __VLS_159 = __VLS_158({
    prop: "target_ref",
    label: "目标",
}, ...__VLS_functionalComponentArgsRest(__VLS_158));
const __VLS_162 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_163 = __VLS_asFunctionalComponent(__VLS_162, new __VLS_162({
    label: "状态",
    width: "110",
}));
const __VLS_164 = __VLS_163({
    label: "状态",
    width: "110",
}, ...__VLS_functionalComponentArgsRest(__VLS_163));
const { default: __VLS_166 } = __VLS_165.slots;
{
    const { default: __VLS_167 } = __VLS_165.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_167);
    (__VLS_ctx.zhStatus(scope.row.status));
    // @ts-ignore
    [zhStatus,];
}
var __VLS_165;
const __VLS_168 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({
    prop: "backup_status",
    label: "备份/快照",
    width: "140",
}));
const __VLS_170 = __VLS_169({
    prop: "backup_status",
    label: "备份/快照",
    width: "140",
}, ...__VLS_functionalComponentArgsRest(__VLS_169));
const __VLS_173 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_174 = __VLS_asFunctionalComponent(__VLS_173, new __VLS_173({
    label: "验证",
}));
const __VLS_175 = __VLS_174({
    label: "验证",
}, ...__VLS_functionalComponentArgsRest(__VLS_174));
const { default: __VLS_177 } = __VLS_176.slots;
{
    const { default: __VLS_178 } = __VLS_176.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_178);
    (scope.row.verifications.map((item) => `${__VLS_ctx.zhStatus(item.status)}：${item.details}`).join("；"));
    // @ts-ignore
    [zhStatus,];
}
var __VLS_176;
const __VLS_179 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_180 = __VLS_asFunctionalComponent(__VLS_179, new __VLS_179({
    label: "操作",
    width: "130",
}));
const __VLS_181 = __VLS_180({
    label: "操作",
    width: "130",
}, ...__VLS_functionalComponentArgsRest(__VLS_180));
const { default: __VLS_183 } = __VLS_182.slots;
{
    const { default: __VLS_184 } = __VLS_182.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_184);
    if (scope.row.rollback_available && __VLS_ctx.capabilities.enabled) {
        // @ts-ignore
        [capabilities,];
        const __VLS_185 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_186 = __VLS_asFunctionalComponent(__VLS_185, new __VLS_185({
            ...{ 'onClick': {} },
            type: "danger",
            size: "small",
        }));
        const __VLS_187 = __VLS_186({
            ...{ 'onClick': {} },
            type: "danger",
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_186));
        let __VLS_189;
        let __VLS_190;
        const __VLS_191 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(scope.row.rollback_available && __VLS_ctx.capabilities.enabled))
                        return;
                    __VLS_ctx.requestRollback(scope.row);
                    // @ts-ignore
                    [requestRollback,];
                } });
        const { default: __VLS_192 } = __VLS_188.slots;
        var __VLS_188;
    }
    else {
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    }
}
var __VLS_182;
var __VLS_149;
/** @type {__VLS_StyleScopedClasses['controlled-page']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['mode-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['controlled-form']} */ ;
/** @type {__VLS_StyleScopedClasses['form-note']} */ ;
/** @type {__VLS_StyleScopedClasses['dry-run-card']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        zhStatus: zhStatus,
        capabilities: capabilities,
        tool: tool,
        service: service,
        targetId: targetId,
        content: content,
        pid: pid,
        preview: preview,
        error: error,
        submitting: submitting,
        approvals: approvals,
        executions: executions,
        prepare: prepare,
        refreshApprovals: refreshApprovals,
        execute: execute,
        requestRollback: requestRollback,
        loadExecutions: loadExecutions,
        argumentText: argumentText,
        toolText: toolText,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
