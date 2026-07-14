import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";
import { zhStatus } from "../status";
const rows = ref([]), loading = ref(false), error = ref("");
async function load() { loading.value = true; error.value = ""; try {
    rows.value = await api("/approvals");
}
catch (e) {
    error.value = e instanceof Error ? e.message : "审批列表加载失败";
}
finally {
    loading.value = false;
} }
async function decide(id, action) { try {
    const reason = await ElMessageBox.prompt(`确认${action === "approve" ? "执行" : "取消"}此 L3 操作？请输入公开理由。`, "操作确认", { confirmButtonText: "确认", cancelButtonText: "返回", inputPattern: /.+/, inputErrorMessage: "必须填写理由", type: action === "approve" ? "warning" : "error" });
    await api(`/approvals/${id}/${action}`, { method: "POST", body: JSON.stringify({ reason: reason.value }) });
    ElMessage.success("确认结果已写入防篡改审计链");
    await load();
}
catch (e) {
    if (e !== "cancel" && e !== "close")
        error.value = e instanceof Error ? e.message : "确认失败";
} }
function summary(value) { return Object.entries(value).map(([key, item]) => `${key}=${item}`).join(" · ") || "无公开参数"; }
onMounted(load);
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_elements;
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel-head" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
const __VLS_0 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onClick': {} },
    loading: (__VLS_ctx.loading),
}));
const __VLS_2 = __VLS_1({
    ...{ 'onClick': {} },
    loading: (__VLS_ctx.loading),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
const __VLS_6 = ({ click: {} },
    { onClick: (__VLS_ctx.load) });
const { default: __VLS_7 } = __VLS_3.slots;
// @ts-ignore
[loading, load,];
var __VLS_3;
if (__VLS_ctx.error) {
    // @ts-ignore
    [error,];
    const __VLS_8 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    ElAlert;
    // @ts-ignore
    const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
        title: (__VLS_ctx.error),
        type: "error",
    }));
    const __VLS_10 = __VLS_9({
        title: (__VLS_ctx.error),
        type: "error",
    }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    // @ts-ignore
    [error,];
}
const __VLS_13 = {}.ElTable;
/** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
// @ts-ignore
ElTable;
// @ts-ignore
const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
    data: (__VLS_ctx.rows),
}));
const __VLS_15 = __VLS_14({
    data: (__VLS_ctx.rows),
}, ...__VLS_functionalComponentArgsRest(__VLS_14));
const { default: __VLS_17 } = __VLS_16.slots;
// @ts-ignore
[rows,];
const __VLS_18 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_19 = __VLS_asFunctionalComponent(__VLS_18, new __VLS_18({
    prop: "tool_name",
    label: "运维动作",
    width: "180",
}));
const __VLS_20 = __VLS_19({
    prop: "tool_name",
    label: "运维动作",
    width: "180",
}, ...__VLS_functionalComponentArgsRest(__VLS_19));
const __VLS_23 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_24 = __VLS_asFunctionalComponent(__VLS_23, new __VLS_23({
    label: "目标参数",
}));
const __VLS_25 = __VLS_24({
    label: "目标参数",
}, ...__VLS_functionalComponentArgsRest(__VLS_24));
const { default: __VLS_27 } = __VLS_26.slots;
{
    const { default: __VLS_28 } = __VLS_26.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_28);
    __VLS_asFunctionalElement(__VLS_elements.code, __VLS_elements.code)({});
    (__VLS_ctx.summary(scope.row.arguments_summary));
    // @ts-ignore
    [summary,];
}
var __VLS_26;
const __VLS_29 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_30 = __VLS_asFunctionalComponent(__VLS_29, new __VLS_29({
    prop: "arguments_hash",
    label: "完整参数哈希",
    showOverflowTooltip: true,
}));
const __VLS_31 = __VLS_30({
    prop: "arguments_hash",
    label: "完整参数哈希",
    showOverflowTooltip: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_30));
const __VLS_34 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_35 = __VLS_asFunctionalComponent(__VLS_34, new __VLS_34({
    label: "风险",
    width: "90",
}));
const __VLS_36 = __VLS_35({
    label: "风险",
    width: "90",
}, ...__VLS_functionalComponentArgsRest(__VLS_35));
const { default: __VLS_38 } = __VLS_37.slots;
{
    const { default: __VLS_39 } = __VLS_37.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_39);
    const __VLS_40 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    ElTag;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        type: "danger",
    }));
    const __VLS_42 = __VLS_41({
        type: "danger",
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    const { default: __VLS_44 } = __VLS_43.slots;
    (scope.row.risk_level);
    var __VLS_43;
}
var __VLS_37;
const __VLS_45 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_46 = __VLS_asFunctionalComponent(__VLS_45, new __VLS_45({
    label: "状态",
    width: "110",
}));
const __VLS_47 = __VLS_46({
    label: "状态",
    width: "110",
}, ...__VLS_functionalComponentArgsRest(__VLS_46));
const { default: __VLS_49 } = __VLS_48.slots;
{
    const { default: __VLS_50 } = __VLS_48.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_50);
    (__VLS_ctx.zhStatus(scope.row.status));
    // @ts-ignore
    [zhStatus,];
}
var __VLS_48;
const __VLS_51 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
ElTableColumn;
// @ts-ignore
const __VLS_52 = __VLS_asFunctionalComponent(__VLS_51, new __VLS_51({
    label: "确认操作",
    width: "180",
}));
const __VLS_53 = __VLS_52({
    label: "确认操作",
    width: "180",
}, ...__VLS_functionalComponentArgsRest(__VLS_52));
const { default: __VLS_55 } = __VLS_54.slots;
{
    const { default: __VLS_56 } = __VLS_54.slots;
    const [scope] = __VLS_getSlotParameters(__VLS_56);
    if (scope.row.status === 'PENDING') {
        const __VLS_57 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_58 = __VLS_asFunctionalComponent(__VLS_57, new __VLS_57({
            ...{ 'onClick': {} },
            size: "small",
            type: "success",
        }));
        const __VLS_59 = __VLS_58({
            ...{ 'onClick': {} },
            size: "small",
            type: "success",
        }, ...__VLS_functionalComponentArgsRest(__VLS_58));
        let __VLS_61;
        let __VLS_62;
        const __VLS_63 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(scope.row.status === 'PENDING'))
                        return;
                    __VLS_ctx.decide(scope.row.id, 'approve');
                    // @ts-ignore
                    [decide,];
                } });
        const { default: __VLS_64 } = __VLS_60.slots;
        var __VLS_60;
        const __VLS_65 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        ElButton;
        // @ts-ignore
        const __VLS_66 = __VLS_asFunctionalComponent(__VLS_65, new __VLS_65({
            ...{ 'onClick': {} },
            size: "small",
            type: "danger",
        }));
        const __VLS_67 = __VLS_66({
            ...{ 'onClick': {} },
            size: "small",
            type: "danger",
        }, ...__VLS_functionalComponentArgsRest(__VLS_66));
        let __VLS_69;
        let __VLS_70;
        const __VLS_71 = ({ click: {} },
            { onClick: (...[$event]) => {
                    if (!(scope.row.status === 'PENDING'))
                        return;
                    __VLS_ctx.decide(scope.row.id, 'reject');
                    // @ts-ignore
                    [decide,];
                } });
        const { default: __VLS_72 } = __VLS_68.slots;
        var __VLS_68;
    }
    else {
        __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    }
}
var __VLS_54;
var __VLS_16;
if (!__VLS_ctx.loading && !__VLS_ctx.rows.length) {
    // @ts-ignore
    [loading, rows,];
    const __VLS_73 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    ElEmpty;
    // @ts-ignore
    const __VLS_74 = __VLS_asFunctionalComponent(__VLS_73, new __VLS_73({
        description: "暂无待确认操作",
    }));
    const __VLS_75 = __VLS_74({
        description: "暂无待确认操作",
    }, ...__VLS_functionalComponentArgsRest(__VLS_74));
}
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        zhStatus: zhStatus,
        rows: rows,
        loading: loading,
        error: error,
        load: load,
        decide: decide,
        summary: summary,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
