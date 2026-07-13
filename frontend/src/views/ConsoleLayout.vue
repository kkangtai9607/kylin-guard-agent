<template>
  <div class="shell">
    <aside>
      <div class="logo"><span>KG</span><div>麒麟智维盾<small>安全智能运维平台</small></div></div>
      <nav><RouterLink v-for="item in nav" :key="item.path" :to="item.path">{{item.label}}</RouterLink></nav>
    </aside>
    <main>
      <header>
        <div><h2>{{$route.meta.title}}</h2><span class="status-dot">安全策略运行正常</span></div>
        <div class="mode"><span class="mode-badge">{{zhStatus(session.mode)}}</span>{{session.username}} <el-button text @click="logout">退出登录</el-button></div>
      </header>
      <section class="content"><RouterView/></section>
    </main>
  </div>
</template>
<script setup lang="ts">
import { useRouter } from "vue-router";
import { useSession } from "../stores/session";
import { zhStatus } from "../status";
const session=useSession(),router=useRouter();
const nav=[
  {path:"/",label:"运维驾驶舱"},{path:"/tasks",label:"智能运维对话"},{path:"/demo",label:"安全演示闭环"},
  {path:"/timeline",label:"任务时间线"},{path:"/approvals",label:"安全审批中心"},{path:"/controlled",label:"受控操作台"},{path:"/mcp",label:"MCP 工具中心"},
  {path:"/inspections",label:"安全巡检"},{path:"/incidents",label:"故障事件与根因分析"},{path:"/drift",label:"配置漂移"},
  {path:"/knowledge",label:"知识库"},{path:"/audit",label:"审计日志"},{path:"/settings",label:"系统设置"},
];
function logout(){session.logout();router.push("/login")}
</script>
