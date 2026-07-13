import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { zhStatus } from "../status";
const capabilities = reactive({ enabled: false, mode: "READ_ONLY", allowed_services: [], managed_configs: [], managed_processes: [] });
const tool = ref("service_restart"), service = ref("nginx"), targetId = ref("nginx-main"), content = ref(""), pid = ref(2), preview = ref(), error = ref(""), submitting = ref(false), approvals = ref([]), executions = ref([]), taskIds = ref([]);
const actionArguments = reactive({});
async function loadCapabilities() { Object.assign(capabilities, await api("/controlled/capabilities")); service.value = capabilities.allowed_services[0] || ""; targetId.value = capabilities.managed_configs[0]?.target_id || ""; }
async function prepare() { submitting.value = true; error.value = ""; try {
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
    ElMessage.success("审批申请已创建，请切换独立审批账号处理");
    await refreshApprovals();
}
catch (e) {
    error.value = e instanceof Error ? e.message : "受控操作准备失败";
}
finally {
    submitting.value = false;
} }
async function refreshApprovals() { const collected = []; for (const taskId of taskIds.value) {
    collected.push(...await api(`/tasks/${taskId}/approvals`));
} approvals.value = collected; }
async function execute(approval) { try {
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
} }
async function requestRollback(execution) { try {
    const args = { change_id: execution.change_id };
    const approval = await api(`/tasks/${execution.task_id}/approvals`, { method: "POST", body: JSON.stringify({ tool_name: "rollback_change", arguments: args }) });
    if (!taskIds.value.includes(execution.task_id))
        taskIds.value.push(execution.task_id);
    actionArguments[approval.id] = args;
    ElMessage.success("回滚审批申请已创建");
    await refreshApprovals();
}
catch (e) {
    error.value = e instanceof Error ? e.message : "回滚申请失败";
} }
async function loadExecutions() { executions.value = await api("/executions"); }
function goalText() { if (tool.value === "service_restart")
    return `重启白名单服务 ${service.value}`; if (tool.value === "config_safe_update")
    return `安全更新托管配置 ${targetId.value}`; return `终止受控托管进程 PID ${pid.value}`; }
function argumentText(value) { return Object.entries(value).map(([key, item]) => `${key}=${item}`).join(" · "); }
onMounted(async () => { try {
    await loadCapabilities();
    await loadExecutions();
}
catch (e) {
    error.value = e instanceof Error ? e.message : "页面加载失败";
} });
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
        title: "当前不是受控执行模式",
        description: "页面允许查看设计，但所有写操作按钮均已禁用。请勿通过前端尝试提升服务器模式。",
        type: "warning",
        showIcon: true,
    }));
    const __VLS_2 = __VLS_1({
        title: "当前不是受控执行模式",
        description: "页面允许查看设计，但所有写操作按钮均已禁用。请勿通过前端尝试提升服务器模式。",
        type: "warning",
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
    emptyText: "本页面尚未创建审批申请",
}));
const __VLS_103 = __VLS_102({
    data: (__VLS_ctx.approvals),
    emptyText: "本页面尚未创建审批申请",
}, ...__VLS_functionalComponentArgsRest(__VLS_102));
const { default: __VLS_105 } = __VLS_104.slots;
// @ts-ignore
[approvals,];
const __VLS_106 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_107 = __VLS_asFunctionalComponent(__VLS_106, new __VLS_106({
    prop: "tool_name",
    label: "工具",
    width: "190",
}));
const __VLS_108 = __VLS_107({
    prop: "tool_name",
    label: "工具",
    width: "190",
}, ...__VLS_functionalComponentArgsRest(__VLS_107));
const __VLS_111 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_112 = __VLS_asFunctionalComponent(__VLS_111, new __VLS_111({
    label: "参数摘要",
}));
const __VLS_113 = __VLS_112({
    label: "参数摘要",
}, ...__VLS_functionalComponentArgsRest(__VLS_112));
const { default: __VLS_115 } = __VLS_114.slots;
{
    const { default: __VLS_116 } = __VLS_114.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_116);
    (__VLS_ctx.argumentText(scope.row.arguments_summary));
    // @ts-ignore
    [argumentText,];
}
var __VLS_114;
const __VLS_117 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_118 = __VLS_asFunctionalComponent(__VLS_117, new __VLS_117({
    label: "状态",
    width: "110",
}));
const __VLS_119 = __VLS_118({
    label: "状态",
    width: "110",
}, ...__VLS_functionalComponentArgsRest(__VLS_118));
const { default: __VLS_121 } = __VLS_120.slots;
{
    const { default: __VLS_122 } = __VLS_120.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_122);
    (__VLS_ctx.zhStatus(scope.row.status));
    // @ts-ignore
    [zhStatus,];
}
var __VLS_120;
const __VLS_123 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_124 = __VLS_asFunctionalComponent(__VLS_123, new __VLS_123({
    label: "操作",
    width: "180",
}));
const __VLS_125 = __VLS_124({
    label: "操作",
    width: "180",
}, ...__VLS_functionalComponentArgsRest(__VLS_124));
const { default: __VLS_127 } = __VLS_126.slots;
{
    const { default: __VLS_128 } = __VLS_126.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_128);
    if (scope.row.status === 'APPROVED') {
        const __VLS_129 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_130 = __VLS_asFunctionalComponent(__VLS_129, new __VLS_129({
            ...{ 'onClick': {} },
            type: "success",
            size: "small",
        }));
        const __VLS_131 = __VLS_130({
            ...{ 'onClick': {} },
            type: "success",
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_130));
        let __VLS_133;
        let __VLS_134;
        const __VLS_135 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(scope.row.status === 'APPROVED'))
                        return;
                    __VLS_ctx.execute(scope.row);
                    // @ts-ignore
                    [execute,];
                } });
        const { default: __VLS_136 } = __VLS_132.slots;
        var __VLS_132;
    }
    else if (scope.row.status === 'PENDING') {
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    }
    else {
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    }
}
var __VLS_126;
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
const __VLS_137 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_138 = __VLS_asFunctionalComponent(__VLS_137, new __VLS_137({
    ...{ 'onClick': {} },
}));
const __VLS_139 = __VLS_138({
    ...{ 'onClick': {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_138));
let __VLS_141;
let __VLS_142;
const __VLS_143 = ({ click: {} },
    { onClick: (__VLS_ctx.loadExecutions) });
const { default: __VLS_144 } = __VLS_140.slots;
// @ts-ignore
[loadExecutions,];
var __VLS_140;
const __VLS_145 = {}.ElTable;
/** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
// @ts-ignore
ElTable;
// @ts-ignore
const __VLS_146 = __VLS_asFunctionalComponent(__VLS_145, new __VLS_145({
    data: (__VLS_ctx.executions),
    emptyText: "暂无执行记录",
}));
const __VLS_147 = __VLS_146({
    data: (__VLS_ctx.executions),
    emptyText: "暂无执行记录",
}, ...__VLS_functionalComponentArgsRest(__VLS_146));
const { default: __VLS_149 } = __VLS_148.slots;
// @ts-ignore
[executions,];
const __VLS_150 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_151 = __VLS_asFunctionalComponent(__VLS_150, new __VLS_150({
    prop: "tool_name",
    label: "工具",
    width: "180",
}));
const __VLS_152 = __VLS_151({
    prop: "tool_name",
    label: "工具",
    width: "180",
}, ...__VLS_functionalComponentArgsRest(__VLS_151));
const __VLS_155 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_156 = __VLS_asFunctionalComponent(__VLS_155, new __VLS_155({
    prop: "target_ref",
    label: "目标",
}));
const __VLS_157 = __VLS_156({
    prop: "target_ref",
    label: "目标",
}, ...__VLS_functionalComponentArgsRest(__VLS_156));
const __VLS_160 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_161 = __VLS_asFunctionalComponent(__VLS_160, new __VLS_160({
    label: "状态",
    width: "110",
}));
const __VLS_162 = __VLS_161({
    label: "状态",
    width: "110",
}, ...__VLS_functionalComponentArgsRest(__VLS_161));
const { default: __VLS_164 } = __VLS_163.slots;
{
    const { default: __VLS_165 } = __VLS_163.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_165);
    (__VLS_ctx.zhStatus(scope.row.status));
    // @ts-ignore
    [zhStatus,];
}
var __VLS_163;
const __VLS_166 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_167 = __VLS_asFunctionalComponent(__VLS_166, new __VLS_166({
    prop: "backup_status",
    label: "备份/快照",
    width: "140",
}));
const __VLS_168 = __VLS_167({
    prop: "backup_status",
    label: "备份/快照",
    width: "140",
}, ...__VLS_functionalComponentArgsRest(__VLS_167));
const __VLS_171 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_172 = __VLS_asFunctionalComponent(__VLS_171, new __VLS_171({
    label: "验证",
}));
const __VLS_173 = __VLS_172({
    label: "验证",
}, ...__VLS_functionalComponentArgsRest(__VLS_172));
const { default: __VLS_175 } = __VLS_174.slots;
{
    const { default: __VLS_176 } = __VLS_174.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_176);
    (scope.row.verifications.map((item) => `${item.status}: ${item.details}`).join('；'));
}
var __VLS_174;
const __VLS_177 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_178 = __VLS_asFunctionalComponent(__VLS_177, new __VLS_177({
    label: "操作",
    width: "130",
}));
const __VLS_179 = __VLS_178({
    label: "操作",
    width: "130",
}, ...__VLS_functionalComponentArgsRest(__VLS_178));
const { default: __VLS_181 } = __VLS_180.slots;
{
    const { default: __VLS_182 } = __VLS_180.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_182);
    if (scope.row.rollback_available && __VLS_ctx.capabilities.enabled) {
        // @ts-ignore
        [capabilities,];
        const __VLS_183 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_184 = __VLS_asFunctionalComponent(__VLS_183, new __VLS_183({
            ...{ 'onClick': {} },
            type: "danger",
            size: "small",
        }));
        const __VLS_185 = __VLS_184({
            ...{ 'onClick': {} },
            type: "danger",
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_184));
        let __VLS_187;
        let __VLS_188;
        const __VLS_189 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(scope.row.rollback_available && __VLS_ctx.capabilities.enabled))
                        return;
                    __VLS_ctx.requestRollback(scope.row);
                    // @ts-ignore
                    [requestRollback,];
                } });
        const { default: __VLS_190 } = __VLS_186.slots;
        var __VLS_186;
    }
    else {
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    }
}
var __VLS_180;
var __VLS_148;
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
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
