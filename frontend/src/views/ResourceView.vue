<template><div class="panel"><div class="panel-head"><div><h3>{{$route.meta.title}}</h3><p>数据来源：麒麟智维盾受控接口</p></div><el-button @click="load" :loading="loading">刷新</el-button></div><el-alert v-if="error" :title="error" type="warning" show-icon/><el-table v-if="rows.length" :data="rows"><el-table-column v-for="key in keys" :key="key" :prop="key" :label="labels[key]||key" show-overflow-tooltip><template #default="scope">{{format(scope.row[key])}}</template></el-table-column></el-table><el-empty v-else-if="!loading&&!error" description="当前没有可展示记录"/><pre v-if="raw">{{raw}}</pre></div></template>
<script setup lang="ts">
import{computed,onMounted,ref,watch}from"vue";import{useRoute}from"vue-router";import{api}from"../api";import{zhStatus}from"../status";
const route=useRoute(),loading=ref(false),error=ref(""),rows=ref<Record<string,unknown>[]>([]),raw=ref("");const endpoint=computed(()=>String(route.meta.endpoint||""));
const labels:Record<string,string>={event_id:"事件编号",event_type:"事件类型",task_id:"任务编号",timestamp:"时间",name:"工具名称",title_zh:"中文名称",risk_level:"风险等级",read_only:"只读工具",status:"状态",duration_ms:"耗时（毫秒）"};
const keys=computed(()=>rows.value.length?Object.keys(rows.value[0]).filter(k=>!["payload","previous_hash","current_hash"].includes(k)).slice(0,7):[]);
function format(v:unknown){if(typeof v==="boolean")return v?"是":"否";if(v==null)return"—";return zhStatus(v)}
async function load(){loading.value=true;error.value="";rows.value=[];raw.value="";try{const data=await api<unknown>(endpoint.value);if(Array.isArray(data))rows.value=data as Record<string,unknown>[];else raw.value=JSON.stringify(data,null,2)}catch(e){error.value=e instanceof Error?e.message:"加载失败"}finally{loading.value=false}}
onMounted(load);watch(endpoint,load);
</script>
