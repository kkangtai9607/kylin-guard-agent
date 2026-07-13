import { useRouter } from "vue-router";
import { useSession } from "../stores/session";
import { zhStatus } from "../status";
const session = useSession(), router = useRouter();
const nav = [
    { path: "/", label: "运维驾驶舱" }, { path: "/tasks", label: "智能运维对话" }, { path: "/demo", label: "安全演示闭环" },
    { path: "/timeline", label: "任务时间线" }, { path: "/approvals", label: "安全审批中心" }, { path: "/controlled", label: "受控操作台" }, { path: "/mcp", label: "MCP 工具中心" },
    { path: "/inspections", label: "安全巡检" }, { path: "/incidents", label: "故障事件与根因分析" }, { path: "/drift", label: "配置漂移" },
    { path: "/knowledge", label: "知识库" }, { path: "/audit", label: "审计日志" }, { path: "/settings", label: "系统设置" },
];
function logout() { session.logout(); router.push("/login"); }
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_elements;
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "shell" },
});
__VLS_asFunctionalElement(__VLS_elements.aside, __VLS_elements.aside)({});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "logo" },
});
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
__VLS_asFunctionalElement(__VLS_elements.small, __VLS_elements.small)({});
__VLS_asFunctionalElement(__VLS_elements.nav, __VLS_elements.nav)({});
for (const [item] of __VLS_getVForSourceType((__VLS_ctx.nav))) {
    // @ts-ignore
    [nav,];
    const __VLS_0 = {}.RouterLink;
    /** @type {[typeof __VLS_components.RouterLink, typeof __VLS_components.RouterLink, ]} */ ;
    // @ts-ignore
    RouterLink;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
        key: (item.path),
        to: (item.path),
    }));
    const __VLS_2 = __VLS_1({
        key: (item.path),
        to: (item.path),
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    const { default: __VLS_4 } = __VLS_3.slots;
    (item.label);
    var __VLS_3;
}
__VLS_asFunctionalElement(__VLS_elements.main, __VLS_elements.main)({});
__VLS_asFunctionalElement(__VLS_elements.header, __VLS_elements.header)({});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({});
__VLS_asFunctionalElement(__VLS_elements.h2, __VLS_elements.h2)({});
(__VLS_ctx.$route.meta.title);
// @ts-ignore
[$route,];
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({
    ...{ class: "status-dot" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "mode" },
});
__VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({
    ...{ class: "mode-badge" },
});
(__VLS_ctx.zhStatus(__VLS_ctx.session.mode));
// @ts-ignore
[zhStatus, session,];
(__VLS_ctx.session.username);
// @ts-ignore
[session,];
const __VLS_5 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
    ...{ 'onClick': {} },
    text: true,
}));
const __VLS_7 = __VLS_6({
    ...{ 'onClick': {} },
    text: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_6));
let __VLS_9;
let __VLS_10;
const __VLS_11 = ({ click: {} },
    { onClick: (__VLS_ctx.logout) });
const { default: __VLS_12 } = __VLS_8.slots;
// @ts-ignore
[logout,];
var __VLS_8;
__VLS_asFunctionalElement(__VLS_elements.section, __VLS_elements.section)({
    ...{ class: "content" },
});
const __VLS_13 = {}.RouterView;
/** @type {[typeof __VLS_components.RouterView, ]} */ ;
// @ts-ignore
RouterView;
// @ts-ignore
const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({}));
const __VLS_15 = __VLS_14({}, ...__VLS_functionalComponentArgsRest(__VLS_14));
/** @type {__VLS_StyleScopedClasses['shell']} */ ;
/** @type {__VLS_StyleScopedClasses['logo']} */ ;
/** @type {__VLS_StyleScopedClasses['status-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['mode']} */ ;
/** @type {__VLS_StyleScopedClasses['mode-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['content']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        zhStatus: zhStatus,
        session: session,
        nav: nav,
        logout: logout,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
