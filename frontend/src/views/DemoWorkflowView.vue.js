import { computed, reactive, ref } from "vue";
import { api, apiAs } from "../api";
import { useSession } from "../stores/session";
import { zhStatus } from "../status";
const session = useSession(), enabled = computed(() => session.mode === "DEMO"), stage = ref("IDLE"), scenario = ref("cleanup"), preview = ref(), approvalId = ref(""), taskId = ref(""), approvalToken = ref(""), approverToken = ref(""), argumentsValue = ref({}), result = ref(), auditValid = ref(null), error = ref("");
const approver = reactive({ username: "", password: "" });
const stageText = computed(() => ({ IDLE: "等待选择场景", WAITING_APPROVAL: "dry-run 通过，等待审批", APPROVED: "审批通过，等待执行", DONE: "执行闭环完成" }[stage.value] || stage.value));
const scenarioText = computed(() => scenario.value === "cleanup" ? "安全日志清理" : "配置验证失败自动回滚");
const previewText = computed(() => preview.value ? JSON.stringify(preview.value, null, 2) : "尚未执行 dry-run");
async function prepare(kind) { error.value = ""; result.value = undefined; scenario.value = kind; try {
    const reset = await api("/demo/reset", { method: "POST" });
    argumentsValue.value = kind === "cleanup" ? { candidate_id: reset.log_candidate_id } : { candidate_id: reset.config_candidate_id, content: "server { listen 9090; }\n" };
    const tool = kind === "cleanup" ? "safe_log_cleanup" : "config_safe_update";
    preview.value = await api("/executions/dry-run", { method: "POST", body: JSON.stringify({ tool_name: tool, arguments: argumentsValue.value }) });
    const task = await api("/tasks", { method: "POST", body: JSON.stringify({ goal: `DEMO ${scenarioText.value}`, requested_mode: "DEMO" }) });
    taskId.value = task.id;
    const approval = await api(`/tasks/${task.id}/approvals`, { method: "POST", body: JSON.stringify({ tool_name: tool, arguments: argumentsValue.value }) });
    approvalId.value = approval.id;
    stage.value = "WAITING_APPROVAL";
}
catch (e) {
    error.value = e instanceof Error ? e.message : "场景准备失败";
} }
async function approve() { error.value = ""; try {
    const login = await apiAs("/auth/login", null, { method: "POST", body: JSON.stringify(approver) });
    approver.password = "";
    approverToken.value = login.access_token;
    await apiAs(`/approvals/${approvalId.value}/approve`, login.access_token, { method: "POST", body: JSON.stringify({ reason: "演示资源、影响范围、备份和回滚方案已人工复核" }) });
    const claimed = await api(`/approvals/${approvalId.value}/claim`, { method: "POST" });
    approvalToken.value = claimed.approval_token;
    stage.value = "APPROVED";
}
catch (e) {
    approver.password = "";
    error.value = e instanceof Error ? e.message : "审批失败";
} }
async function execute() { error.value = ""; try {
    const tool = scenario.value === "cleanup" ? "safe_log_cleanup" : "config_safe_update";
    result.value = await api("/executions/run", { method: "POST", body: JSON.stringify({ task_id: taskId.value, tool_name: tool, arguments: argumentsValue.value, approval_token: approvalToken.value, ...(scenario.value === "rollback" ? { fault: "verification" } : {}) }) });
    approvalToken.value = "";
    stage.value = "DONE";
    await verifyAudit();
}
catch (e) {
    approvalToken.value = "";
    error.value = e instanceof Error ? e.message : "执行失败";
} }
async function verifyAudit() { try {
    const value = approverToken.value ? await apiAs("/audit/verify", approverToken.value) : await api("/audit/verify");
    auditValid.value = value.valid;
}
catch (e) {
    error.value = e instanceof Error ? e.message : "审计校验失败";
} }
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_elements;
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "demo-workflow" },
});
if (!__VLS_ctx.enabled) {
    // @ts-ignore
    [enabled,];
    const __VLS_0 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    ElAlert;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
        title: "当前不是演示模式",
        description: "为保护真实系统，本页面只在独立 DEMO 服务中启用；READ_ONLY 和 CONTROLLED_EXECUTION 均不能在此执行。",
        type: "warning",
        showIcon: true,
    }));
    const __VLS_2 = __VLS_1({
        title: "当前不是演示模式",
        description: "为保护真实系统，本页面只在独立 DEMO 服务中启用；READ_ONLY 和 CONTROLLED_EXECUTION 均不能在此执行。",
        type: "warning",
        showIcon: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
}
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
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
(__VLS_ctx.zhStatus(__VLS_ctx.session.mode));
// @ts-ignore
[zhStatus, session,];
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "demo-actions" },
});
const __VLS_5 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
    ...{ 'onClick': {} },
    type: "primary",
    disabled: (!__VLS_ctx.enabled),
}));
const __VLS_7 = __VLS_6({
    ...{ 'onClick': {} },
    type: "primary",
    disabled: (!__VLS_ctx.enabled),
}, ...__VLS_functionalComponentArgsRest(__VLS_6));
let __VLS_9;
let __VLS_10;
const __VLS_11 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.prepare('cleanup');
            // @ts-ignore
            [enabled, prepare,];
        } });
const { default: __VLS_12 } = __VLS_8.slots;
var __VLS_8;
const __VLS_13 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
    ...{ 'onClick': {} },
    type: "danger",
    disabled: (!__VLS_ctx.enabled),
}));
const __VLS_15 = __VLS_14({
    ...{ 'onClick': {} },
    type: "danger",
    disabled: (!__VLS_ctx.enabled),
}, ...__VLS_functionalComponentArgsRest(__VLS_14));
let __VLS_17;
let __VLS_18;
const __VLS_19 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.prepare('rollback');
            // @ts-ignore
            [enabled, prepare,];
        } });
const { default: __VLS_20 } = __VLS_16.slots;
var __VLS_16;
const __VLS_21 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_22 = __VLS_asFunctionalComponent(__VLS_21, new __VLS_21({
    ...{ 'onClick': {} },
}));
const __VLS_23 = __VLS_22({
    ...{ 'onClick': {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_22));
let __VLS_25;
let __VLS_26;
const __VLS_27 = ({ click: {} },
    { onClick: (__VLS_ctx.verifyAudit) });
const { default: __VLS_28 } = __VLS_24.slots;
// @ts-ignore
[verifyAudit,];
var __VLS_24;
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "demo-grid" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel" },
});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "demo-state" },
});
__VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({});
(__VLS_ctx.stageText);
// @ts-ignore
[stageText,];
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
(__VLS_ctx.scenarioText);
// @ts-ignore
[scenarioText,];
__VLS_asFunctionalElement(__VLS_elements.pre, __VLS_elements.pre)({});
(__VLS_ctx.previewText);
// @ts-ignore
[previewText,];
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel" },
});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
const __VLS_29 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
ElInput;
// @ts-ignore
const __VLS_30 = __VLS_asFunctionalComponent(__VLS_29, new __VLS_29({
    modelValue: (__VLS_ctx.approver.username),
    placeholder: "审批员用户名",
}));
const __VLS_31 = __VLS_30({
    modelValue: (__VLS_ctx.approver.username),
    placeholder: "审批员用户名",
}, ...__VLS_functionalComponentArgsRest(__VLS_30));
// @ts-ignore
[approver,];
const __VLS_34 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
ElInput;
// @ts-ignore
const __VLS_35 = __VLS_asFunctionalComponent(__VLS_34, new __VLS_34({
    modelValue: (__VLS_ctx.approver.password),
    type: "password",
    showPassword: true,
    placeholder: "审批员密码",
}));
const __VLS_36 = __VLS_35({
    modelValue: (__VLS_ctx.approver.password),
    type: "password",
    showPassword: true,
    placeholder: "审批员密码",
}, ...__VLS_functionalComponentArgsRest(__VLS_35));
// @ts-ignore
[approver,];
const __VLS_39 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_40 = __VLS_asFunctionalComponent(__VLS_39, new __VLS_39({
    ...{ 'onClick': {} },
    type: "success",
    disabled: (__VLS_ctx.stage !== 'WAITING_APPROVAL'),
}));
const __VLS_41 = __VLS_40({
    ...{ 'onClick': {} },
    type: "success",
    disabled: (__VLS_ctx.stage !== 'WAITING_APPROVAL'),
}, ...__VLS_functionalComponentArgsRest(__VLS_40));
let __VLS_43;
let __VLS_44;
const __VLS_45 = ({ click: {} },
    { onClick: (__VLS_ctx.approve) });
const { default: __VLS_46 } = __VLS_42.slots;
// @ts-ignore
[stage, approve,];
var __VLS_42;
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel" },
});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
const __VLS_47 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_48 = __VLS_asFunctionalComponent(__VLS_47, new __VLS_47({
    ...{ 'onClick': {} },
    ...{ class: "task-primary" },
    type: "primary",
    disabled: (__VLS_ctx.stage !== 'APPROVED'),
}));
const __VLS_49 = __VLS_48({
    ...{ 'onClick': {} },
    ...{ class: "task-primary" },
    type: "primary",
    disabled: (__VLS_ctx.stage !== 'APPROVED'),
}, ...__VLS_functionalComponentArgsRest(__VLS_48));
let __VLS_51;
let __VLS_52;
const __VLS_53 = ({ click: {} },
    { onClick: (__VLS_ctx.execute) });
const { default: __VLS_54 } = __VLS_50.slots;
// @ts-ignore
[stage, execute,];
var __VLS_50;
if (__VLS_ctx.result) {
    // @ts-ignore
    [result,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "result-card" },
    });
    __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({
        ...{ class: "state-chip" },
        ...{ class: (__VLS_ctx.result.status === 'ROLLED_BACK' ? 'warning' : '') },
    });
    // @ts-ignore
    [result,];
    (__VLS_ctx.zhStatus(__VLS_ctx.result.status));
    // @ts-ignore
    [zhStatus, result,];
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    (__VLS_ctx.result.backup_ref ? '已创建' : '不适用');
    // @ts-ignore
    [result,];
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    (__VLS_ctx.result.verification);
    // @ts-ignore
    [result,];
    if (__VLS_ctx.result.rollback_status) {
        // @ts-ignore
        [result,];
        __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
        (__VLS_ctx.zhStatus(__VLS_ctx.result.rollback_status));
        // @ts-ignore
        [zhStatus, result,];
    }
}
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel" },
});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "health-row" },
});
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
__VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({
    ...{ class: "state-chip" },
    ...{ class: (__VLS_ctx.auditValid === false ? 'warning' : '') },
});
// @ts-ignore
[auditValid,];
(__VLS_ctx.auditValid === null ? '尚未校验' : __VLS_ctx.auditValid ? '完整有效' : '校验失败');
// @ts-ignore
[auditValid, auditValid,];
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
if (__VLS_ctx.error) {
    // @ts-ignore
    [error,];
    const __VLS_55 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    ElAlert;
    // @ts-ignore
    const __VLS_56 = __VLS_asFunctionalComponent(__VLS_55, new __VLS_55({
        title: (__VLS_ctx.error),
        type: "error",
        showIcon: true,
    }));
    const __VLS_57 = __VLS_56({
        title: (__VLS_ctx.error),
        type: "error",
        showIcon: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_56));
    // @ts-ignore
    [error,];
}
/** @type {__VLS_StyleScopedClasses['demo-workflow']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['mode-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['demo-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['demo-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['demo-state']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['task-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['result-card']} */ ;
/** @type {__VLS_StyleScopedClasses['state-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['health-row']} */ ;
/** @type {__VLS_StyleScopedClasses['state-chip']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        zhStatus: zhStatus,
        session: session,
        enabled: enabled,
        stage: stage,
        result: result,
        auditValid: auditValid,
        error: error,
        approver: approver,
        stageText: stageText,
        scenarioText: scenarioText,
        previewText: previewText,
        prepare: prepare,
        approve: approve,
        execute: execute,
        verifyAudit: verifyAudit,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
