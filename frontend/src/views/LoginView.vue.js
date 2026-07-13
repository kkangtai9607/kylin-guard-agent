import { ref } from "vue";
import { useRouter } from "vue-router";
import { useSession } from "../stores/session";
const username = ref(""), password = ref(""), error = ref(""), loading = ref(false), router = useRouter(), session = useSession();
async function submit() { loading.value = true; error.value = ""; try {
    await session.login(username.value, password.value);
    await router.push("/");
}
catch (e) {
    error.value = e instanceof Error ? e.message : "登录失败";
}
finally {
    password.value = "";
    loading.value = false;
} }
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_elements;
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "login-shell" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "login-card" },
});
__VLS_asFunctionalElement(__VLS_elements.div, __VLS_elements.div)({
    ...{ class: "brand-mark" },
});
__VLS_asFunctionalElement(__VLS_elements.h1, __VLS_elements.h1)({});
__VLS_asFunctionalElement(__VLS_elements.p, __VLS_elements.p)({});
const __VLS_0 = {}.ElForm;
/** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
// @ts-ignore
ElForm;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onSubmit': {} },
}));
const __VLS_2 = __VLS_1({
    ...{ 'onSubmit': {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
const __VLS_6 = ({ submit: {} },
    { onSubmit: (__VLS_ctx.submit) });
const { default: __VLS_7 } = __VLS_3.slots;
// @ts-ignore
[submit,];
const __VLS_8 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
ElInput;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    modelValue: (__VLS_ctx.username),
    placeholder: "用户名",
}));
const __VLS_10 = __VLS_9({
    modelValue: (__VLS_ctx.username),
    placeholder: "用户名",
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
// @ts-ignore
[username,];
const __VLS_13 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
ElInput;
// @ts-ignore
const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
    modelValue: (__VLS_ctx.password),
    type: "password",
    showPassword: true,
    placeholder: "密码",
}));
const __VLS_15 = __VLS_14({
    modelValue: (__VLS_ctx.password),
    type: "password",
    showPassword: true,
    placeholder: "密码",
}, ...__VLS_functionalComponentArgsRest(__VLS_14));
// @ts-ignore
[password,];
if (__VLS_ctx.error) {
    // @ts-ignore
    [error,];
    const __VLS_18 = {}.ElAlert;
    /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
    // @ts-ignore
    ElAlert;
    // @ts-ignore
    const __VLS_19 = __VLS_asFunctionalComponent(__VLS_18, new __VLS_18({
        title: (__VLS_ctx.error),
        type: "error",
        closable: (false),
    }));
    const __VLS_20 = __VLS_19({
        title: (__VLS_ctx.error),
        type: "error",
        closable: (false),
    }, ...__VLS_functionalComponentArgsRest(__VLS_19));
    // @ts-ignore
    [error,];
}
const __VLS_23 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
ElButton;
// @ts-ignore
const __VLS_24 = __VLS_asFunctionalComponent(__VLS_23, new __VLS_23({
    nativeType: "submit",
    type: "primary",
    loading: (__VLS_ctx.loading),
}));
const __VLS_25 = __VLS_24({
    nativeType: "submit",
    type: "primary",
    loading: (__VLS_ctx.loading),
}, ...__VLS_functionalComponentArgsRest(__VLS_24));
const { default: __VLS_27 } = __VLS_26.slots;
// @ts-ignore
[loading,];
var __VLS_26;
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['login-shell']} */ ;
/** @type {__VLS_StyleScopedClasses['login-card']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-mark']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup: () => ({
        username: username,
        password: password,
        error: error,
        loading: loading,
        submit: submit,
    }),
});
export default (await import('vue')).defineComponent({});
; /* PartiallyEnd: #4569/main.vue */
