import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import { zhStatus } from "../status";
const route = useRoute(), loading = ref(false), error = ref(""), rows = ref([]), raw = ref("");
const endpoint = computed(() => String(route.meta.endpoint || ""));
const labels = { event_id: "事件编号", event_type: "事件类型", task_id: "任务编号", timestamp: "时间", name: "工具名称", title_zh: "中文名称", risk_level: "风险等级", read_only: "只读工具", status: "状态", duration_ms: "耗时（毫秒）" };
const keys = computed(() => rows.value.length ? Object.keys(rows.value[0]).filter(k => !["payload", "previous_hash", "current_hash"].includes(k)).slice(0, 7) : []);
function format(v) { if (typeof v === "boolean")
    return v ? "是" : "否"; if (v == null)
    return "—"; return zhStatus(v); }
async function load() { loading.value = true; error.value = ""; rows.value = []; raw.value = ""; try {
    const data = await api(endpoint.value);
    if (Array.isArray(data))
        rows.value = data;
    else
        raw.value = JSON.stringify(data, null, 2);
}
catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
}
finally {
    loading.value = false;
} }
onMounted(load);
watch(endpoint, load);
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
(__VLS_ctx.$route.meta.title);
// @ts-ignore
[$route,];
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
        type: "warning",
        showIcon: true,
    }));
    const __VLS_10 = __VLS_9({
        title: (__VLS_ctx.error),
        type: "warning",
        showIcon: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    // @ts-ignore
    [error,];
}
if (__VLS_ctx.rows.length) {
    // @ts-ignore
    [rows,];
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
    for (const [key] of __VLS_getVForSourceType((__VLS_ctx.keys))) {
        // @ts-ignore
        [keys,];
        const __VLS_18 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_19 = __VLS_asFunctionalComponent(__VLS_18, new __VLS_18({
            key: (key),
            prop: (key),
            label: (__VLS_ctx.labels[key] || key),
            showOverflowTooltip: true,
        }));
        const __VLS_20 = __VLS_19({
            key: (key),
            prop: (key),
            label: (__VLS_ctx.labels[key] || key),
            showOverflowTooltip: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_19));
        const { default: __VLS_22 } = __VLS_21.slots;
        // @ts-ignore
        [labels,];
        {
            const { default: __VLS_23 } = __VLS_21.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_23);
            (__VLS_ctx.format(scope.row[key]));
            // @ts-ignore
            [format,];
        }
        var __VLS_21;
    }
    var __VLS_16;
}
else if (!__VLS_ctx.loading && !__VLS_ctx.error) {
    // @ts-ignore
    [loading, error,];
    const __VLS_24 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    ElEmpty;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
        description: "当前没有可展示记录",
    }));
    const __VLS_26 = __VLS_25({
        description: "当前没有可展示记录",
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
}
if (__VLS_ctx.raw) {
    // @ts-ignore
    [raw,];
    __VLS_asFunctionalElement(__VLS_elements.pre, __VLS_elements.pre)({});
    (__VLS_ctx.raw);
    // @ts-ignore
    [raw,];
}
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        loading: loading,
        error: error,
        rows: rows,
        raw: raw,
        labels: labels,
        keys: keys,
        format: format,
        load: load,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
