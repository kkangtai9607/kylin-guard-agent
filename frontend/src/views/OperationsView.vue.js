import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import { zhStatus } from "../status";
const route = useRoute(), kind = computed(() => String(route.meta.kind)), title = computed(() => String(route.meta.title));
const descriptions = { inspections: "巡检会读取系统快照、磁盘阈值、服务状态、监听端口、僵尸进程、procfs/systemctl/journalctl 可用性和工具注册完整性；异常由规则生成事件。", incidents: "跟踪巡检产生的故障和安全事件。", drift: "建立脱敏基线并比较当前配置。", knowledge: "未审核知识不能支持高风险执行。", audit: "查询、验证并导出防篡改审计链。", settings: "管理非秘密参数，密钥只能通过环境变量注入。" };
const endpoints = { inspections: "/inspections", incidents: "/incidents", drift: "/config-drift", knowledge: "/knowledge", audit: "/audit/events", settings: "/settings" };
const labels = { id: "编号", document_id: "文档编号", title: "标题", summary: "摘要", severity: "级别", status: "状态", path_ref: "配置标识", created_at: "时间", captured_at: "采集时间", event_type: "事件类型" };
const rows = ref([]), raw = ref(""), error = ref(""), result = ref(""), query = ref("Linux"), form = reactive({ path_ref: "", document_id: "", title: "", content: "" }), settings = reactive({ snapshot_interval_seconds: 300, retention_days: 30 });
const keys = computed(() => rows.value.length ? Object.keys(rows.value[0]).filter(k => !["payload", "previous_hash", "current_hash"].includes(k)).slice(0, 6) : []);
function format(v) { if (typeof v === "boolean")
    return v ? "是" : "否"; if (v == null)
    return "—"; return zhStatus(v); }
async function load() { error.value = ""; try {
    const suffix = kind.value === "knowledge" ? `?query=${encodeURIComponent(query.value)}` : "", data = await api(endpoints[kind.value] + suffix);
    if (kind.value === "settings")
        Object.assign(settings, data);
    else if (Array.isArray(data))
        rows.value = data;
    else
        raw.value = JSON.stringify(data, null, 2);
}
catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
} }
async function act(fn) { try {
    await fn();
    await load();
}
catch (e) {
    error.value = e instanceof Error ? e.message : "操作失败";
} }
const post = (p, b) => api(p, { method: "POST", body: b ? JSON.stringify(b) : undefined }), put = (p, b) => api(p, { method: "PUT", body: JSON.stringify(b) });
const runInspection = () => act(async () => { await post("/inspections/run"); }), baseline = () => act(async () => { await post("/config-drift/baselines", { path_ref: form.path_ref, content: form.content }); }), drift = () => act(async () => { raw.value = JSON.stringify(await post("/config-drift/check", { path_ref: form.path_ref, current_content: form.content }), null, 2); }), addKnowledge = () => act(async () => { await post("/knowledge", { document_id: form.document_id, title: form.title, content: form.content, review_status: "PENDING" }); }), review = (id, status) => act(async () => { await put(`/knowledge/${id}`, { review_status: status }); }), incident = (id, status) => act(async () => { await put(`/incidents/${id}`, { status }); }), saveSettings = () => act(async () => { await put("/settings", settings); }), verifyAudit = () => act(async () => { result.value = JSON.stringify(await api("/audit/verify")); });
async function exportAudit() { await act(async () => { const data = await api("/audit/export"), url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)])), a = document.createElement("a"); a.href = url; a.download = "麒麟智维盾-审计记录.json"; a.click(); URL.revokeObjectURL(url); }); }
onMounted(load);
watch(kind, load);
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
(__VLS_ctx.title);
// @ts-ignore
[title,];
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
(__VLS_ctx.descriptions[__VLS_ctx.kind]);
// @ts-ignore
[descriptions, kind,];
const __VLS_0 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onClick': {} },
}));
const __VLS_2 = __VLS_1({
    ...{ 'onClick': {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
const __VLS_6 = ({ click: {} },
    { onClick: (__VLS_ctx.load) });
const { default: __VLS_7 } = __VLS_3.slots;
// @ts-ignore
[load,];
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
if (__VLS_ctx.kind === 'inspections') {
    // @ts-ignore
    [kind,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "action-row" },
    });
    const __VLS_13 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    ElButton;
    // @ts-ignore
    const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
        ...{ 'onClick': {} },
        type: "primary",
    }));
    const __VLS_15 = __VLS_14({
        ...{ 'onClick': {} },
        type: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_14));
    let __VLS_17;
    let __VLS_18;
    const __VLS_19 = ({ click: {} },
        { onClick: (__VLS_ctx.runInspection) });
    const { default: __VLS_20 } = __VLS_16.slots;
    // @ts-ignore
    [runInspection,];
    var __VLS_16;
    __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
}
if (__VLS_ctx.kind === 'drift') {
    // @ts-ignore
    [kind,];
    const __VLS_21 = {}.ElForm;
    /** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
    // @ts-ignore
    ElForm;
    // @ts-ignore
    const __VLS_22 = __VLS_asFunctionalComponent(__VLS_21, new __VLS_21({
        ...{ class: "action-form" },
        labelPosition: "top",
    }));
    const __VLS_23 = __VLS_22({
        ...{ class: "action-form" },
        labelPosition: "top",
    }, ...__VLS_functionalComponentArgsRest(__VLS_22));
    const { default: __VLS_25 } = __VLS_24.slots;
    const __VLS_26 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_27 = __VLS_asFunctionalComponent(__VLS_26, new __VLS_26({
        label: "配置标识",
    }));
    const __VLS_28 = __VLS_27({
        label: "配置标识",
    }, ...__VLS_functionalComponentArgsRest(__VLS_27));
    const { default: __VLS_30 } = __VLS_29.slots;
    const __VLS_31 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    ElInput;
    // @ts-ignore
    const __VLS_32 = __VLS_asFunctionalComponent(__VLS_31, new __VLS_31({
        modelValue: (__VLS_ctx.form.path_ref),
    }));
    const __VLS_33 = __VLS_32({
        modelValue: (__VLS_ctx.form.path_ref),
    }, ...__VLS_functionalComponentArgsRest(__VLS_32));
    // @ts-ignore
    [form,];
    var __VLS_29;
    const __VLS_36 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        label: "配置内容（敏感行自动脱敏）",
    }));
    const __VLS_38 = __VLS_37({
        label: "配置内容（敏感行自动脱敏）",
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    const { default: __VLS_40 } = __VLS_39.slots;
    const __VLS_41 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    ElInput;
    // @ts-ignore
    const __VLS_42 = __VLS_asFunctionalComponent(__VLS_41, new __VLS_41({
        modelValue: (__VLS_ctx.form.content),
        type: "textarea",
        rows: (5),
    }));
    const __VLS_43 = __VLS_42({
        modelValue: (__VLS_ctx.form.content),
        type: "textarea",
        rows: (5),
    }, ...__VLS_functionalComponentArgsRest(__VLS_42));
    // @ts-ignore
    [form,];
    var __VLS_39;
    const __VLS_46 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    ElButton;
    // @ts-ignore
    const __VLS_47 = __VLS_asFunctionalComponent(__VLS_46, new __VLS_46({
        ...{ 'onClick': {} },
        type: "primary",
    }));
    const __VLS_48 = __VLS_47({
        ...{ 'onClick': {} },
        type: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_47));
    let __VLS_50;
    let __VLS_51;
    const __VLS_52 = ({ click: {} },
        { onClick: (__VLS_ctx.baseline) });
    const { default: __VLS_53 } = __VLS_49.slots;
    // @ts-ignore
    [baseline,];
    var __VLS_49;
    const __VLS_54 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    ElButton;
    // @ts-ignore
    const __VLS_55 = __VLS_asFunctionalComponent(__VLS_54, new __VLS_54({
        ...{ 'onClick': {} },
    }));
    const __VLS_56 = __VLS_55({
        ...{ 'onClick': {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_55));
    let __VLS_58;
    let __VLS_59;
    const __VLS_60 = ({ click: {} },
        { onClick: (__VLS_ctx.drift) });
    const { default: __VLS_61 } = __VLS_57.slots;
    // @ts-ignore
    [drift,];
    var __VLS_57;
    var __VLS_24;
}
if (__VLS_ctx.kind === 'knowledge') {
    // @ts-ignore
    [kind,];
    const __VLS_62 = {}.ElForm;
    /** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
    // @ts-ignore
    ElForm;
    // @ts-ignore
    const __VLS_63 = __VLS_asFunctionalComponent(__VLS_62, new __VLS_62({
        ...{ class: "action-form" },
        labelPosition: "top",
    }));
    const __VLS_64 = __VLS_63({
        ...{ class: "action-form" },
        labelPosition: "top",
    }, ...__VLS_functionalComponentArgsRest(__VLS_63));
    const { default: __VLS_66 } = __VLS_65.slots;
    const __VLS_67 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_68 = __VLS_asFunctionalComponent(__VLS_67, new __VLS_67({
        label: "检索",
    }));
    const __VLS_69 = __VLS_68({
        label: "检索",
    }, ...__VLS_functionalComponentArgsRest(__VLS_68));
    const { default: __VLS_71 } = __VLS_70.slots;
    const __VLS_72 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    ElInput;
    // @ts-ignore
    const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
        ...{ 'onKeyup': {} },
        modelValue: (__VLS_ctx.query),
    }));
    const __VLS_74 = __VLS_73({
        ...{ 'onKeyup': {} },
        modelValue: (__VLS_ctx.query),
    }, ...__VLS_functionalComponentArgsRest(__VLS_73));
    let __VLS_76;
    let __VLS_77;
    const __VLS_78 = ({ keyup: {} },
        { onKeyup: (__VLS_ctx.load) });
    // @ts-ignore
    [load, query,];
    var __VLS_75;
    var __VLS_70;
    const __VLS_80 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
        label: "文档编号",
    }));
    const __VLS_82 = __VLS_81({
        label: "文档编号",
    }, ...__VLS_functionalComponentArgsRest(__VLS_81));
    const { default: __VLS_84 } = __VLS_83.slots;
    const __VLS_85 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    ElInput;
    // @ts-ignore
    const __VLS_86 = __VLS_asFunctionalComponent(__VLS_85, new __VLS_85({
        modelValue: (__VLS_ctx.form.document_id),
    }));
    const __VLS_87 = __VLS_86({
        modelValue: (__VLS_ctx.form.document_id),
    }, ...__VLS_functionalComponentArgsRest(__VLS_86));
    // @ts-ignore
    [form,];
    var __VLS_83;
    const __VLS_90 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_91 = __VLS_asFunctionalComponent(__VLS_90, new __VLS_90({
        label: "标题",
    }));
    const __VLS_92 = __VLS_91({
        label: "标题",
    }, ...__VLS_functionalComponentArgsRest(__VLS_91));
    const { default: __VLS_94 } = __VLS_93.slots;
    const __VLS_95 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    ElInput;
    // @ts-ignore
    const __VLS_96 = __VLS_asFunctionalComponent(__VLS_95, new __VLS_95({
        modelValue: (__VLS_ctx.form.title),
    }));
    const __VLS_97 = __VLS_96({
        modelValue: (__VLS_ctx.form.title),
    }, ...__VLS_functionalComponentArgsRest(__VLS_96));
    // @ts-ignore
    [form,];
    var __VLS_93;
    const __VLS_100 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
        label: "内容",
    }));
    const __VLS_102 = __VLS_101({
        label: "内容",
    }, ...__VLS_functionalComponentArgsRest(__VLS_101));
    const { default: __VLS_104 } = __VLS_103.slots;
    const __VLS_105 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    ElInput;
    // @ts-ignore
    const __VLS_106 = __VLS_asFunctionalComponent(__VLS_105, new __VLS_105({
        modelValue: (__VLS_ctx.form.content),
        type: "textarea",
        rows: (4),
    }));
    const __VLS_107 = __VLS_106({
        modelValue: (__VLS_ctx.form.content),
        type: "textarea",
        rows: (4),
    }, ...__VLS_functionalComponentArgsRest(__VLS_106));
    // @ts-ignore
    [form,];
    var __VLS_103;
    const __VLS_110 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    ElButton;
    // @ts-ignore
    const __VLS_111 = __VLS_asFunctionalComponent(__VLS_110, new __VLS_110({
        ...{ 'onClick': {} },
        type: "primary",
    }));
    const __VLS_112 = __VLS_111({
        ...{ 'onClick': {} },
        type: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_111));
    let __VLS_114;
    let __VLS_115;
    const __VLS_116 = ({ click: {} },
        { onClick: (__VLS_ctx.addKnowledge) });
    const { default: __VLS_117 } = __VLS_113.slots;
    // @ts-ignore
    [addKnowledge,];
    var __VLS_113;
    var __VLS_65;
}
if (__VLS_ctx.kind === 'settings') {
    // @ts-ignore
    [kind,];
    const __VLS_118 = {}.ElForm;
    /** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
    // @ts-ignore
    ElForm;
    // @ts-ignore
    const __VLS_119 = __VLS_asFunctionalComponent(__VLS_118, new __VLS_118({
        ...{ class: "action-form" },
        labelPosition: "top",
    }));
    const __VLS_120 = __VLS_119({
        ...{ class: "action-form" },
        labelPosition: "top",
    }, ...__VLS_functionalComponentArgsRest(__VLS_119));
    const { default: __VLS_122 } = __VLS_121.slots;
    const __VLS_123 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_124 = __VLS_asFunctionalComponent(__VLS_123, new __VLS_123({
        label: "快照间隔（秒）",
    }));
    const __VLS_125 = __VLS_124({
        label: "快照间隔（秒）",
    }, ...__VLS_functionalComponentArgsRest(__VLS_124));
    const { default: __VLS_127 } = __VLS_126.slots;
    const __VLS_128 = {}.ElInputNumber;
    /** @type {[typeof __VLS_components.ElInputNumber, typeof __VLS_components.elInputNumber, ]} */ ;
    // @ts-ignore
    ElInputNumber;
    // @ts-ignore
    const __VLS_129 = __VLS_asFunctionalComponent(__VLS_128, new __VLS_128({
        modelValue: (__VLS_ctx.settings.snapshot_interval_seconds),
        min: (30),
        max: (86400),
    }));
    const __VLS_130 = __VLS_129({
        modelValue: (__VLS_ctx.settings.snapshot_interval_seconds),
        min: (30),
        max: (86400),
    }, ...__VLS_functionalComponentArgsRest(__VLS_129));
    // @ts-ignore
    [settings,];
    var __VLS_126;
    const __VLS_133 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    ElFormItem;
    // @ts-ignore
    const __VLS_134 = __VLS_asFunctionalComponent(__VLS_133, new __VLS_133({
        label: "保留天数",
    }));
    const __VLS_135 = __VLS_134({
        label: "保留天数",
    }, ...__VLS_functionalComponentArgsRest(__VLS_134));
    const { default: __VLS_137 } = __VLS_136.slots;
    const __VLS_138 = {}.ElInputNumber;
    /** @type {[typeof __VLS_components.ElInputNumber, typeof __VLS_components.elInputNumber, ]} */ ;
    // @ts-ignore
    ElInputNumber;
    // @ts-ignore
    const __VLS_139 = __VLS_asFunctionalComponent(__VLS_138, new __VLS_138({
        modelValue: (__VLS_ctx.settings.retention_days),
        min: (1),
        max: (365),
    }));
    const __VLS_140 = __VLS_139({
        modelValue: (__VLS_ctx.settings.retention_days),
        min: (1),
        max: (365),
    }, ...__VLS_functionalComponentArgsRest(__VLS_139));
    // @ts-ignore
    [settings,];
    var __VLS_136;
    const __VLS_143 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    ElButton;
    // @ts-ignore
    const __VLS_144 = __VLS_asFunctionalComponent(__VLS_143, new __VLS_143({
        ...{ 'onClick': {} },
        type: "primary",
    }));
    const __VLS_145 = __VLS_144({
        ...{ 'onClick': {} },
        type: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_144));
    let __VLS_147;
    let __VLS_148;
    const __VLS_149 = ({ click: {} },
        { onClick: (__VLS_ctx.saveSettings) });
    const { default: __VLS_150 } = __VLS_146.slots;
    // @ts-ignore
    [saveSettings,];
    var __VLS_146;
    var __VLS_121;
}
if (__VLS_ctx.kind === 'audit') {
    // @ts-ignore
    [kind,];
    __VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
        ...{ class: "action-row" },
    });
    const __VLS_151 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    ElButton;
    // @ts-ignore
    const __VLS_152 = __VLS_asFunctionalComponent(__VLS_151, new __VLS_151({
        ...{ 'onClick': {} },
        type: "primary",
    }));
    const __VLS_153 = __VLS_152({
        ...{ 'onClick': {} },
        type: "primary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_152));
    let __VLS_155;
    let __VLS_156;
    const __VLS_157 = ({ click: {} },
        { onClick: (__VLS_ctx.verifyAudit) });
    const { default: __VLS_158 } = __VLS_154.slots;
    // @ts-ignore
    [verifyAudit,];
    var __VLS_154;
    const __VLS_159 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    ElButton;
    // @ts-ignore
    const __VLS_160 = __VLS_asFunctionalComponent(__VLS_159, new __VLS_159({
        ...{ 'onClick': {} },
    }));
    const __VLS_161 = __VLS_160({
        ...{ 'onClick': {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_160));
    let __VLS_163;
    let __VLS_164;
    const __VLS_165 = ({ click: {} },
        { onClick: (__VLS_ctx.exportAudit) });
    const { default: __VLS_166 } = __VLS_162.slots;
    // @ts-ignore
    [exportAudit,];
    var __VLS_162;
    __VLS_asFunctionalElement(__VLS_elements.span, __VLS_elements.span)({});
    (__VLS_ctx.result);
    // @ts-ignore
    [result,];
}
if (__VLS_ctx.rows.length) {
    // @ts-ignore
    [rows,];
    const __VLS_167 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    ElTable;
    // @ts-ignore
    const __VLS_168 = __VLS_asFunctionalComponent(__VLS_167, new __VLS_167({
        data: (__VLS_ctx.rows),
    }));
    const __VLS_169 = __VLS_168({
        data: (__VLS_ctx.rows),
    }, ...__VLS_functionalComponentArgsRest(__VLS_168));
    const { default: __VLS_171 } = __VLS_170.slots;
    // @ts-ignore
    [rows,];
    for (const [key] of __VLS_getVForSourceType((__VLS_ctx.keys))) {
        // @ts-ignore
        [keys,];
        const __VLS_172 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_173 = __VLS_asFunctionalComponent(__VLS_172, new __VLS_172({
            key: (key),
            label: (__VLS_ctx.labels[key] || key),
        }));
        const __VLS_174 = __VLS_173({
            key: (key),
            label: (__VLS_ctx.labels[key] || key),
        }, ...__VLS_functionalComponentArgsRest(__VLS_173));
        const { default: __VLS_176 } = __VLS_175.slots;
        // @ts-ignore
        [labels,];
        {
            const { default: __VLS_177 } = __VLS_175.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_177);
            (__VLS_ctx.format(scope.row[key]));
            // @ts-ignore
            [format,];
        }
        var __VLS_175;
    }
    if (__VLS_ctx.kind === 'incidents') {
        // @ts-ignore
        [kind,];
        const __VLS_178 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_179 = __VLS_asFunctionalComponent(__VLS_178, new __VLS_178({
            label: "操作",
            width: "190",
        }));
        const __VLS_180 = __VLS_179({
            label: "操作",
            width: "190",
        }, ...__VLS_functionalComponentArgsRest(__VLS_179));
        const { default: __VLS_182 } = __VLS_181.slots;
        {
            const { default: __VLS_183 } = __VLS_181.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_183);
            const __VLS_184 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_185 = __VLS_asFunctionalComponent(__VLS_184, new __VLS_184({
                ...{ 'onClick': {} },
                size: "small",
            }));
            const __VLS_186 = __VLS_185({
                ...{ 'onClick': {} },
                size: "small",
            }, ...__VLS_functionalComponentArgsRest(__VLS_185));
            let __VLS_188;
            let __VLS_189;
            const __VLS_190 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.rows.length))
                            return;
                        if (!(__VLS_ctx.kind === 'incidents'))
                            return;
                        __VLS_ctx.incident(scope.row.id, 'ACKNOWLEDGED');
                        // @ts-ignore
                        [incident,];
                    } });
            const { default: __VLS_191 } = __VLS_187.slots;
            var __VLS_187;
            const __VLS_192 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_193 = __VLS_asFunctionalComponent(__VLS_192, new __VLS_192({
                ...{ 'onClick': {} },
                size: "small",
                type: "success",
            }));
            const __VLS_194 = __VLS_193({
                ...{ 'onClick': {} },
                size: "small",
                type: "success",
            }, ...__VLS_functionalComponentArgsRest(__VLS_193));
            let __VLS_196;
            let __VLS_197;
            const __VLS_198 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.rows.length))
                            return;
                        if (!(__VLS_ctx.kind === 'incidents'))
                            return;
                        __VLS_ctx.incident(scope.row.id, 'RESOLVED');
                        // @ts-ignore
                        [incident,];
                    } });
            const { default: __VLS_199 } = __VLS_195.slots;
            var __VLS_195;
        }
        var __VLS_181;
    }
    if (__VLS_ctx.kind === 'knowledge') {
        // @ts-ignore
        [kind,];
        const __VLS_200 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        ElTableColumn;
        // @ts-ignore
        const __VLS_201 = __VLS_asFunctionalComponent(__VLS_200, new __VLS_200({
            label: "审核",
            width: "180",
        }));
        const __VLS_202 = __VLS_201({
            label: "审核",
            width: "180",
        }, ...__VLS_functionalComponentArgsRest(__VLS_201));
        const { default: __VLS_204 } = __VLS_203.slots;
        {
            const { default: __VLS_205 } = __VLS_203.slots;
            const [scope] = __VLS_getSlotParameters(__VLS_205);
            const __VLS_206 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_207 = __VLS_asFunctionalComponent(__VLS_206, new __VLS_206({
                ...{ 'onClick': {} },
                size: "small",
                type: "success",
            }));
            const __VLS_208 = __VLS_207({
                ...{ 'onClick': {} },
                size: "small",
                type: "success",
            }, ...__VLS_functionalComponentArgsRest(__VLS_207));
            let __VLS_210;
            let __VLS_211;
            const __VLS_212 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.rows.length))
                            return;
                        if (!(__VLS_ctx.kind === 'knowledge'))
                            return;
                        __VLS_ctx.review(scope.row.document_id, 'APPROVED');
                        // @ts-ignore
                        [review,];
                    } });
            const { default: __VLS_213 } = __VLS_209.slots;
            var __VLS_209;
            const __VLS_214 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            ElButton;
            // @ts-ignore
            const __VLS_215 = __VLS_asFunctionalComponent(__VLS_214, new __VLS_214({
                ...{ 'onClick': {} },
                size: "small",
                type: "danger",
            }));
            const __VLS_216 = __VLS_215({
                ...{ 'onClick': {} },
                size: "small",
                type: "danger",
            }, ...__VLS_functionalComponentArgsRest(__VLS_215));
            let __VLS_218;
            let __VLS_219;
            const __VLS_220 = ({ click: {} },
                { onClick: (...[$event]) => {
                        if (!(__VLS_ctx.rows.length))
                            return;
                        if (!(__VLS_ctx.kind === 'knowledge'))
                            return;
                        __VLS_ctx.review(scope.row.document_id, 'REJECTED');
                        // @ts-ignore
                        [review,];
                    } });
            const { default: __VLS_221 } = __VLS_217.slots;
            var __VLS_217;
        }
        var __VLS_203;
    }
    var __VLS_170;
}
else if (__VLS_ctx.kind !== 'settings') {
    // @ts-ignore
    [kind,];
    const __VLS_222 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    ElEmpty;
    // @ts-ignore
    const __VLS_223 = __VLS_asFunctionalComponent(__VLS_222, new __VLS_222({
        description: "当前没有记录",
    }));
    const __VLS_224 = __VLS_223({
        description: "当前没有记录",
    }, ...__VLS_functionalComponentArgsRest(__VLS_223));
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
/** @type {__VLS_StyleScopedClasses['action-row']} */ ;
/** @type {__VLS_StyleScopedClasses['action-form']} */ ;
/** @type {__VLS_StyleScopedClasses['action-form']} */ ;
/** @type {__VLS_StyleScopedClasses['action-form']} */ ;
/** @type {__VLS_StyleScopedClasses['action-row']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        kind: kind,
        title: title,
        descriptions: descriptions,
        labels: labels,
        rows: rows,
        raw: raw,
        error: error,
        result: result,
        query: query,
        form: form,
        settings: settings,
        keys: keys,
        format: format,
        load: load,
        runInspection: runInspection,
        baseline: baseline,
        drift: drift,
        addKnowledge: addKnowledge,
        review: review,
        incident: incident,
        saveSettings: saveSettings,
        verifyAudit: verifyAudit,
        exportAudit: exportAudit,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
