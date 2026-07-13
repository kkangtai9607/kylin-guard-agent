import { onMounted, ref } from "vue";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { init, use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { api } from "../api";
import { useSession } from "../stores/session";
import { zhStatus } from "../status";
use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);
const session = useSession(), chartEl = ref(), chartMessage = ref("");
const kpis = [{ label: "运行模式", value: "安全默认", note: "默认禁止写操作", tone: "accent" }, { label: "安全等级", value: "L0 至 L4", note: "由规则引擎判定", tone: "" }, { label: "MCP 工具", value: "14 个", note: "系统感知工具", tone: "" }, { label: "审计链", value: "运行正常", note: "事件完整性可验证", tone: "good" }];
onMounted(async () => { try {
    await api("/health");
    const snapshots = await api("/inspections");
    const points = snapshots.slice().reverse().map(i => ({ time: i.captured_at, value: i.payload?.data?.disk?.used })).filter(i => typeof i.value === "number");
    if (points.length < 3)
        chartMessage.value = "至少完成三次巡检后才会生成趋势";
    if (chartEl.value)
        init(chartEl.value).setOption({ tooltip: { trigger: "axis" }, grid: { left: 55, right: 24, top: 25, bottom: 42 }, xAxis: { type: "category", data: points.map(i => new Date(i.time).toLocaleTimeString()) }, yAxis: { type: "value" }, series: [{ type: "line", smooth: true, data: points.map(i => i.value), lineStyle: { color: "#2a78d6", width: 3 }, areaStyle: { color: "#dbeafe" } }] });
}
catch (e) {
    chartMessage.value = e instanceof Error ? e.message : "无法连接服务";
} });
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_elements;
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
const __VLS_0 = {}.ElAlert;
/** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
// @ts-ignore
ElAlert;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    title: "当前展示真实接口数据；运行模式由后端受信任配置决定",
    type: "info",
    showIcon: true,
}));
const __VLS_2 = __VLS_1({
    title: "当前展示真实接口数据；运行模式由后端受信任配置决定",
    type: "info",
    showIcon: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "kpis" },
});
for (const [k] of __VLS_getVForSourceType((__VLS_ctx.kpis))) {
    // @ts-ignore
    [kpis,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        key: (k.label),
        ...{ class: "panel" },
    });
    __VLS_asFunctionalElement(__VLS_elements.small, __VLS_elements.small)({});
    (k.label);
    __VLS_asFunctionalElement(__VLS_elements.strong, __VLS_elements.strong)({
        ...{ class: "kpi-value" },
        ...{ class: (k.tone) },
    });
    (k.value);
    __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    (k.note);
}
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "grid" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel" },
});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "health-card" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "health-row" },
});
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
__VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({
    ...{ class: "state-chip" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "health-row" },
});
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
__VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({
    ...{ class: "state-chip" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "health-row" },
});
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
__VLS_asFunctionalElement(__VLS_elements.b, __VLS_elements.b)({
    ...{ class: "state-chip warning" },
});
(__VLS_ctx.zhStatus(__VLS_ctx.session.mode));
// @ts-ignore
[zhStatus, session,];
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel" },
});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
__VLS_asFunctionalElement(__VLS_elements.ul, __VLS_elements.ul)({});
__VLS_asFunctionalElement(__VLS_elements.li, __VLS_elements.li)({});
__VLS_asFunctionalElement(__VLS_elements.li, __VLS_elements.li)({});
__VLS_asFunctionalElement(__VLS_elements.li, __VLS_elements.li)({});
__VLS_asFunctionalElement(__VLS_elements.li, __VLS_elements.li)({});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "panel chart-panel" },
});
__VLS_asFunctionalElement(__VLS_elements.h3, __VLS_elements.h3)({});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ref: "chartEl",
    ...{ class: "chart" },
});
/** @type {typeof __VLS_ctx.chartEl} */ ;
// @ts-ignore
[chartEl,];
if (__VLS_ctx.chartMessage) {
    // @ts-ignore
    [chartMessage,];
    __VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
    (__VLS_ctx.chartMessage);
    // @ts-ignore
    [chartMessage,];
}
/** @type {__VLS_StyleScopedClasses['kpis']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['kpi-value']} */ ;
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['health-card']} */ ;
/** @type {__VLS_StyleScopedClasses['health-row']} */ ;
/** @type {__VLS_StyleScopedClasses['state-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['health-row']} */ ;
/** @type {__VLS_StyleScopedClasses['state-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['health-row']} */ ;
/** @type {__VLS_StyleScopedClasses['state-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['warning']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['chart']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        zhStatus: zhStatus,
        session: session,
        chartEl: chartEl,
        chartMessage: chartMessage,
        kpis: kpis,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
